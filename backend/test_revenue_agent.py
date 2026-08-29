import pytest
from fastapi.testclient import TestClient
import uuid
from unittest.mock import patch

from main import app
from database import (
    merchants_collection,
    campaigns_collection,
    offers_collection,
    orders_collection,
    customers_collection,
    agent_runs_collection
)

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    merchants_collection.delete_many({"merchant_id": {"$regex": "^test_rev_"}})
    campaigns_collection.delete_many({"merchant_id": {"$regex": "^test_rev_"}})
    offers_collection.delete_many({"merchant_id": {"$regex": "^test_rev_"}})
    orders_collection.delete_many({"merchant_id": {"$regex": "^test_rev_"}})
    customers_collection.delete_many({"merchant_id": {"$regex": "^test_rev_"}})
    agent_runs_collection.delete_many({"merchant_id": {"$regex": "^test_rev_"}})
    
    merchants_collection.insert_one({
        "merchant_id": "test_rev_merchant",
        "rules": {
            "max_discount_percentage": 20.0,
            "min_margin_percentage": 30.0
        }
    })
    
    yield
    
    merchants_collection.delete_many({"merchant_id": {"$regex": "^test_rev_"}})
    campaigns_collection.delete_many({"merchant_id": {"$regex": "^test_rev_"}})
    offers_collection.delete_many({"merchant_id": {"$regex": "^test_rev_"}})
    orders_collection.delete_many({"merchant_id": {"$regex": "^test_rev_"}})
    customers_collection.delete_many({"merchant_id": {"$regex": "^test_rev_"}})
    agent_runs_collection.delete_many({"merchant_id": {"$regex": "^test_rev_"}})

def setup_data_for_agent(merchant_id="test_rev_merchant", campaigns_count=1, offers_count=5):
    customers_collection.insert_one({
        "customer_id": f"cust_{uuid.uuid4()}",
        "merchant_id": merchant_id,
        "segment": "loyal",
        "purchase_count": 5
    })
    
    for i in range(campaigns_count):
        camp_id = f"camp_{uuid.uuid4()}"
        campaigns_collection.insert_one({
            "campaign_id": camp_id,
            "merchant_id": merchant_id,
            "campaign_name": f"Rev Camp {i}",
            "status": "COMPLETED"
        })
        
        for j in range(offers_count):
            offer_id = f"offer_{uuid.uuid4()}"
            offers_collection.insert_one({
                "offer_id": offer_id,
                "campaign_id": camp_id,
                "merchant_id": merchant_id,
                "customer_segment": "new_visitor"
            })
            orders_collection.insert_one({
                "offer_id": offer_id,
                "merchant_id": merchant_id,
                "payment_status": "PAYMENT_VERIFIED",
                "amount": 500000, # 5000 INR
                "razorpay_order_id": f"order_{uuid.uuid4()}"
            })

@patch('claude_agent.get_client')
def test_1_successful_agent_flow_and_guardrail_approval(mock_get_client):
    setup_data_for_agent()
    # Mock AI giving a safe discount to new_visitor (15%)
    mock_get_client.return_value.chat.completions.create.return_value.choices[0].message.content = '''{
        "strategy": "Acquire new customers",
        "recommendation": {
            "segment": "new_visitor",
            "action": "Offer discount",
            "offer": "15% off",
            "discount_percentage": 15
        },
        "reasoning": "Test",
        "priority": "high",
        "evidence": [],
        "confidence": "high",
        "limitations": []
    }'''
    
    response = client.post("/agent/run", json={"merchant_id": "test_rev_merchant"})
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "VALIDATED"
    assert data["data_sufficiency"] == "SUFFICIENT_DATA"
    assert data["guardrail_result"]["status"] == "APPROVED"
    assert data["recommendation"]["discount_percentage"] == 15
    assert data["strategy"] == "Acquire new customers"
    assert data["priority"] == "high"
    assert "score" in data
    assert "score_breakdown" in data
    assert "explanation" in data
    assert data["confidence"] == "medium" # Downgraded due to low historical data quality (1 campaign)
    
    # Verify persistence
    persisted = agent_runs_collection.find_one({"agent_run_id": data["agent_run_id"]})
    assert persisted is not None
    assert persisted["status"] == "VALIDATED"

@patch('claude_agent.get_client')
def test_2_ai_violates_guardrails(mock_get_client):
    setup_data_for_agent()
    # Mock AI giving 30% discount which breaks max 20% rule
    mock_get_client.return_value.chat.completions.create.return_value.choices[0].message.content = '''{
        "strategy": "Aggressive growth",
        "recommendation": {
            "segment": "new_visitor",
            "action": "Offer huge discount",
            "offer": "30% off",
            "discount_percentage": 30
        },
        "reasoning": "Aggressive growth",
        "priority": "high",
        "evidence": [],
        "confidence": "high",
        "limitations": []
    }'''
    
    response = client.post("/agent/run", json={"merchant_id": "test_rev_merchant"})
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "REJECTED"
    assert data["data_sufficiency"] == "SUFFICIENT_DATA"
    assert data["guardrail_result"]["status"] == "REJECTED"
    assert "Recommended discount violates" in data["reason"]
    assert data["score"] == 0

@patch('claude_agent.get_client')
def test_3_ai_violates_loyalty_rule(mock_get_client):
    setup_data_for_agent()
    # Mock AI giving 10% to loyal. Rule: loyal gets max 5%
    mock_get_client.return_value.chat.completions.create.return_value.choices[0].message.content = '''{
        "strategy": "Reward loyalty",
        "recommendation": {
            "segment": "loyal",
            "action": "Reward them",
            "offer": "10% off",
            "discount_percentage": 10
        },
        "reasoning": "Loyalty",
        "priority": "medium",
        "evidence": [],
        "confidence": "high",
        "limitations": []
    }'''
    
    response = client.post("/agent/run", json={"merchant_id": "test_rev_merchant"})
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "REJECTED"
    assert data["guardrail_result"]["status"] == "REJECTED"

@patch('claude_agent.get_client')
def test_4_insufficient_data(mock_get_client):
    # Merchant exists, but 0 campaigns
    mock_get_client.return_value.chat.completions.create.return_value.choices[0].message.content = '''{
        "strategy": "Wait and monitor",
        "recommendation": {
            "segment": "unknown",
            "action": "Wait",
            "offer": "N/A",
            "discount_percentage": 0
        },
        "reasoning": "Campaign is too new to evaluate.",
        "priority": "low",
        "evidence": [],
        "confidence": "low",
        "limitations": []
    }'''
    
    response = client.post("/agent/run", json={"merchant_id": "test_rev_merchant"})
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "INSUFFICIENT_DATA"
    assert data["data_sufficiency"] == "INSUFFICIENT_DATA"
    assert "Wait and monitor" in data["strategy"]
    assert data["recommendation"]["discount_percentage"] == 0
    assert data["confidence"] == "low"
    
    persisted = agent_runs_collection.find_one({"agent_run_id": data["agent_run_id"]})
    assert persisted is not None

@patch('claude_agent.get_client')
def test_5_limited_data_confidence_downgrade(mock_get_client):
    # 1 campaign, 0 offers
    setup_data_for_agent(campaigns_count=1, offers_count=0)
    mock_get_client.return_value.chat.completions.create.return_value.choices[0].message.content = '''{
        "strategy": "Run targeted test",
        "recommendation": {
            "segment": "new_visitor",
            "action": "Offer discount",
            "offer": "10% off",
            "discount_percentage": 10
        },
        "reasoning": "Test",
        "priority": "medium",
        "evidence": [],
        "confidence": "high",
        "limitations": []
    }'''
    response = client.post("/agent/run", json={"merchant_id": "test_rev_merchant"})
    assert response.status_code == 200
    data = response.json()
    
    assert data["data_sufficiency"] == "LIMITED_DATA"
    # Even though AI said 'high', LIMITED_DATA downgrades it, and 1 campaign downgrades again
    assert data["confidence"] == "low"
    assert data["status"] == "VALIDATED"

def test_6_merchant_not_found():
    response = client.post("/agent/run", json={"merchant_id": "fake_merchant"})
    assert response.status_code == 404

@patch('claude_agent.get_client')
def test_7_ai_fallback(mock_get_client):
    setup_data_for_agent()
    class ExplodingClient:
        @property
        def chat(self):
            raise Exception("API Down")
            
    mock_get_client.return_value = ExplodingClient()
    
    response = client.post("/agent/run", json={"merchant_id": "test_rev_merchant"})
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "FAILED"
    assert data["reason"] == "AI recommendation temporarily unavailable"
    assert data["recommendation"] is None
    
    persisted = agent_runs_collection.find_one({"agent_run_id": data["agent_run_id"]})
    assert persisted is not None
    assert persisted["status"] == "FAILED"
