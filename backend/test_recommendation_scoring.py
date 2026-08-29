import pytest
from unittest.mock import patch
import uuid
from fastapi.testclient import TestClient
from main import app
from database import campaigns_collection, offers_collection, orders_collection, merchants_collection
from test_historical_learning import create_historical_data

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    merchants_collection.delete_many({"merchant_id": {"$regex": "^test_score_"}})
    campaigns_collection.delete_many({"merchant_id": {"$regex": "^test_score_"}})
    offers_collection.delete_many({"merchant_id": {"$regex": "^test_score_"}})
    orders_collection.delete_many({"merchant_id": {"$regex": "^test_score_"}})
    
    yield
    
    merchants_collection.delete_many({"merchant_id": {"$regex": "^test_score_"}})
    campaigns_collection.delete_many({"merchant_id": {"$regex": "^test_score_"}})
    offers_collection.delete_many({"merchant_id": {"$regex": "^test_score_"}})
    orders_collection.delete_many({"merchant_id": {"$regex": "^test_score_"}})

def create_merchant(merchant_id):
    merchants_collection.insert_one({
        "merchant_id": merchant_id,
        "rules": {"max_discount_percentage": 20, "min_margin_percentage": 10}
    })

@patch('claude_agent.get_client')
def test_1_high_quality_recommendation(mock_get_client):
    merchant_id = "test_score_high"
    create_merchant(merchant_id)
    # Give strong historical data (3 campaigns) showing new_visitor converts well at 15%
    config = [
        {"segments": {"new_visitor": {"offers": 10, "orders": 5, "discount": 15}}},
        {"segments": {"new_visitor": {"offers": 10, "orders": 4, "discount": 15}}},
        {"segments": {"new_visitor": {"offers": 10, "orders": 6, "discount": 15}}}
    ]
    create_historical_data(merchant_id, config)
    
    mock_get_client.return_value.chat.completions.create.return_value.choices[0].message.content = '''{
        "strategy": "Retarget",
        "recommendation": {
            "segment": "new_visitor",
            "action": "Offer discount",
            "offer": "15% off",
            "discount_percentage": 15
        },
        "reasoning": "Historical data shows new_visitor responds well to 15%",
        "priority": "high",
        "evidence": [],
        "confidence": "high",
        "limitations": []
    }'''
    
    response = client.post("/agent/run", json={"merchant_id": merchant_id})
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "VALIDATED"
    # Data quality = 20 (high)
    # Historical evidence = 30 (segment is best + discount is top)
    # Current performance = 0 (no active campaign data matched)
    # Rule compatibility = 20 (passed)
    assert data["score"] >= 70
    assert data["score_breakdown"]["data_quality"] == 20
    assert data["score_breakdown"]["historical_evidence"] == 30
    assert data["score_breakdown"]["rule_compatibility"] == 20

@patch('claude_agent.get_client')
def test_2_low_data_recommendation(mock_get_client):
    merchant_id = "test_score_low"
    create_merchant(merchant_id)
    # 0 campaigns
    
    mock_get_client.return_value.chat.completions.create.return_value.choices[0].message.content = '''{
        "strategy": "Wait",
        "recommendation": {
            "segment": "unknown",
            "action": "Wait",
            "offer": "N/A",
            "discount_percentage": 0
        },
        "reasoning": "No data",
        "priority": "low",
        "evidence": [],
        "confidence": "low",
        "limitations": []
    }'''
    
    response = client.post("/agent/run", json={"merchant_id": merchant_id})
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "INSUFFICIENT_DATA"
    assert data["score_breakdown"]["data_quality"] == 0
    assert data["score_breakdown"]["historical_evidence"] == 0

@patch('claude_agent.get_client')
def test_8_12_recommendation_violating_max_discount(mock_get_client):
    merchant_id = "test_score_reject"
    create_merchant(merchant_id)
    config = [{"segments": {"loyal": {"offers": 10, "orders": 5, "discount": 10}}}]
    create_historical_data(merchant_id, config)
    
    mock_get_client.return_value.chat.completions.create.return_value.choices[0].message.content = '''{
        "strategy": "Aggressive",
        "recommendation": {
            "segment": "loyal",
            "action": "Offer discount",
            "offer": "30% off",
            "discount_percentage": 30
        },
        "reasoning": "Push hard",
        "priority": "high",
        "evidence": [],
        "confidence": "high",
        "limitations": []
    }'''
    
    response = client.post("/agent/run", json={"merchant_id": merchant_id})
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "REJECTED"
    assert data["score"] == 0
    assert data["score_breakdown"]["rule_compatibility"] == 0
    assert "Recommendation violates merchant business rules." in data["explanation"]

def test_14_15_malformed_response():
    merchant_id = "test_score_malformed"
    create_merchant(merchant_id)
    
    with patch('claude_agent.get_client') as mock_get_client:
        mock_get_client.return_value.chat.completions.create.side_effect = Exception("API Down")
        
        response = client.post("/agent/run", json={"merchant_id": merchant_id})
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "FAILED"
        assert "recommendation temporarily unavailable" in data["reason"]
