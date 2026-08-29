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
    feedback_collection
)

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    merchants_collection.delete_many({"merchant_id": {"$regex": "^test_intel_"}})
    campaigns_collection.delete_many({"merchant_id": {"$regex": "^test_intel_"}})
    offers_collection.delete_many({"merchant_id": {"$regex": "^test_intel_"}})
    orders_collection.delete_many({"merchant_id": {"$regex": "^test_intel_"}})
    feedback_collection.delete_many({"merchant_id": {"$regex": "^test_intel_"}})
    
    merchants_collection.insert_one({"merchant_id": "test_intel_merchant"})
    
    yield
    
    merchants_collection.delete_many({"merchant_id": {"$regex": "^test_intel_"}})
    campaigns_collection.delete_many({"merchant_id": {"$regex": "^test_intel_"}})
    offers_collection.delete_many({"merchant_id": {"$regex": "^test_intel_"}})
    orders_collection.delete_many({"merchant_id": {"$regex": "^test_intel_"}})
    feedback_collection.delete_many({"merchant_id": {"$regex": "^test_intel_"}})

def setup_campaign_data(merchant_id, num_campaigns=2):
    campaign_ids = []
    for i in range(num_campaigns):
        camp_id = f"camp_{uuid.uuid4()}"
        campaigns_collection.insert_one({
            "campaign_id": camp_id,
            "merchant_id": merchant_id,
            "campaign_name": f"Campaign {i}",
            "target_segment": "loyal",
            "status": "COMPLETED"
        })
        campaign_ids.append(camp_id)
        
        # Add offers and payments. Campaign 0 is worst, Campaign 1 is best
        offers_count = 10
        payments_count = 2 if i == 0 else 8 # 20% vs 80% conversion
        
        for j in range(offers_count):
            offer_id = f"offer_{uuid.uuid4()}"
            offers_collection.insert_one({
                "offer_id": offer_id,
                "campaign_id": camp_id,
                "merchant_id": merchant_id,
                "customer_id": f"cust_{j}",
                "customer_segment": "loyal"
            })
            if j < payments_count:
                orders_collection.insert_one({
                    "offer_id": offer_id,
                    "merchant_id": merchant_id,
                    "payment_status": "PAYMENT_VERIFIED",
                    "amount": 10000, # 100 INR
                    "razorpay_order_id": f"order_{uuid.uuid4()}"
                })
                
    # Add some feedback data
    feedback_collection.insert_one({
        "feedback_id": str(uuid.uuid4()),
        "optimization_id": str(uuid.uuid4()),
        "merchant_id": merchant_id,
        "outcome": "IMPROVED"
    })
    feedback_collection.insert_one({
        "feedback_id": str(uuid.uuid4()),
        "optimization_id": str(uuid.uuid4()),
        "merchant_id": merchant_id,
        "outcome": "DECLINED"
    })
    
    return campaign_ids

@patch('claude_agent.get_client')
def test_1_merchant_with_multiple_campaigns_and_test_4_campaign_comparison(mock_get_client):
    mock_get_client.return_value.chat.completions.create.return_value.choices[0].message.content = '{"summary": "Good", "key_findings": ["A", "B"], "opportunities": ["X"], "warnings": ["Y"]}'
    setup_campaign_data("test_intel_merchant", 2)
    
    response = client.get("/merchants/test_intel_merchant/intelligence")
    assert response.status_code == 200
    data = response.json()
    
    assert data["summary"]["total_campaigns"] == 2
    assert len(data["campaign_comparison"]) == 2

@patch('claude_agent.get_client')
def test_2_merchant_with_one_campaign_and_test_11_insufficient_data(mock_get_client):
    mock_get_client.return_value.chat.completions.create.return_value.choices[0].message.content = '{"summary": "Need more data", "key_findings": [], "opportunities": [], "warnings": []}'
    # Test cold start with 0 offers
    camp_id = f"camp_{uuid.uuid4()}"
    campaigns_collection.insert_one({
        "campaign_id": camp_id,
        "merchant_id": "test_intel_merchant",
        "campaign_name": f"Campaign 1",
        "target_segment": "loyal",
        "status": "COMPLETED"
    })
    
    response = client.get("/merchants/test_intel_merchant/intelligence")
    assert response.status_code == 200
    data = response.json()
    
    assert data["summary"]["total_campaigns"] == 1
    assert data["summary"]["total_offers"] == 0
    # Cold start triggers AI replacement
    assert data["ai_insights"]["summary"] == "INSUFFICIENT_DATA"

def test_3_merchant_with_no_campaigns():
    response = client.get("/merchants/test_intel_merchant/intelligence")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_campaigns"] == 0
    assert data["ai_insights"]["summary"] == "INSUFFICIENT_DATA"

@patch('claude_agent.get_client')
def test_5_best_and_test_6_lowest_performing_campaign(mock_get_client):
    mock_get_client.return_value.chat.completions.create.return_value.choices[0].message.content = '{"summary": "Good", "key_findings": ["A", "B"], "opportunities": ["X"], "warnings": ["Y"]}'
    campaign_ids = setup_campaign_data("test_intel_merchant", 2)
    
    response = client.get("/merchants/test_intel_merchant/intelligence")
    assert response.status_code == 200
    data = response.json()
    
    best = data["best_performing_campaign"]
    lowest = data["lowest_performing_campaign"]
    
    assert best["campaign_id"] == campaign_ids[1] # 80% conversion
    assert best["conversion_rate"] == 80.0
    
    assert lowest["campaign_id"] == campaign_ids[0] # 20% conversion
    assert lowest["conversion_rate"] == 20.0

@patch('claude_agent.get_client')
def test_7_segment_aggregation_and_8_9_10_opt_history(mock_get_client):
    mock_get_client.return_value.chat.completions.create.return_value.choices[0].message.content = '{"summary": "Good", "key_findings": ["A", "B"], "opportunities": ["X"], "warnings": ["Y"]}'
    setup_campaign_data("test_intel_merchant", 1)
    
    response = client.get("/merchants/test_intel_merchant/intelligence")
    assert response.status_code == 200
    data = response.json()
    
    # Segment Intel
    assert len(data["segment_intelligence"]) == 1
    assert data["segment_intelligence"][0]["segment"] == "loyal"
    
    # Opt History
    history = data["optimization_history"]
    assert history["improved"] == 1
    assert history["declined"] == 1
    assert history["total_optimizations"] == 2

def test_13_merchant_not_found():
    response = client.get("/merchants/unknown_merchant/intelligence")
    assert response.status_code == 404

@patch('claude_agent.get_client')
def test_14_ai_interpretation_success_and_15_failure(mock_get_client):
    setup_campaign_data("test_intel_merchant", 2)
    
    class ExplodingClient:
        @property
        def chat(self):
            raise Exception("API Down")
            
    mock_get_client.return_value = ExplodingClient()
    
    response = client.get("/merchants/test_intel_merchant/intelligence")
    assert response.status_code == 200
    data = response.json()
    
    # Fallback structure should be intact
    assert data["ai_insights"]["summary"] == "Insights unavailable due to API failure."
    assert data["ai_insights"]["key_findings"] == []
