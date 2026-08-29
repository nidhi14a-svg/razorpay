import pytest
from fastapi.testclient import TestClient
import uuid
from unittest.mock import patch

from main import app
from database import (
    optimizations_collection,
    campaigns_collection,
    feedback_collection,
    merchants_collection,
    offers_collection,
    orders_collection
)
from feedback_service import evaluate_optimization_outcome

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    merchants_collection.delete_many({"merchant_id": {"$regex": "^test_fb_"}})
    campaigns_collection.delete_many({"merchant_id": {"$regex": "^test_fb_"}})
    optimizations_collection.delete_many({"merchant_id": {"$regex": "^test_fb_"}})
    feedback_collection.delete_many({"merchant_id": {"$regex": "^test_fb_"}})
    offers_collection.delete_many({"merchant_id": {"$regex": "^test_fb_"}})
    orders_collection.delete_many({"merchant_id": {"$regex": "^test_fb_"}})
    
    merchants_collection.insert_one({
        "merchant_id": "test_fb_merchant"
    })
    
    yield
    
    merchants_collection.delete_many({"merchant_id": {"$regex": "^test_fb_"}})
    campaigns_collection.delete_many({"merchant_id": {"$regex": "^test_fb_"}})
    optimizations_collection.delete_many({"merchant_id": {"$regex": "^test_fb_"}})
    feedback_collection.delete_many({"merchant_id": {"$regex": "^test_fb_"}})
    offers_collection.delete_many({"merchant_id": {"$regex": "^test_fb_"}})
    orders_collection.delete_many({"merchant_id": {"$regex": "^test_fb_"}})

def setup_opt_and_campaign(status="EXECUTED", before_metrics=None, after_offers=10, after_payments=5, after_revenue=5000):
    camp_id = f"camp_{uuid.uuid4()}"
    opt_id = f"opt_{uuid.uuid4()}"
    
    campaigns_collection.insert_one({
        "campaign_id": camp_id,
        "merchant_id": "test_fb_merchant",
        "campaign_name": "Test Feedback Camp",
        "status": "COMPLETED"
    })
    
    if before_metrics is None:
        before_metrics = {
            "total_offers": 10,
            "verified_payments": 2,
            "revenue": 1000.0,
            "conversion_rate": 20.0,
            "average_order_value": 500.0
        }
        
    optimizations_collection.insert_one({
        "optimization_id": opt_id,
        "campaign_id": camp_id,
        "merchant_id": "test_fb_merchant",
        "status": status,
        "campaign_metrics_snapshot": before_metrics,
        "generated_at": "2024-01-01T00:00:00Z"
    })
    
    # Setup the AFTER metrics dynamically
    for i in range(after_offers):
        offer_id = f"offer_{uuid.uuid4()}"
        offers_collection.insert_one({
            "offer_id": offer_id,
            "campaign_id": camp_id,
            "merchant_id": "test_fb_merchant",
            "customer_id": f"cust_{i}",
            "customer_segment": "new_visitor"
        })
        if i < after_payments:
            orders_collection.insert_one({
                "offer_id": offer_id,
                "merchant_id": "test_fb_merchant",
                "payment_status": "PAYMENT_VERIFIED",
                "amount": int(after_revenue * 100 / after_payments) if after_payments > 0 else 0, # stored in paise
                "razorpay_order_id": f"order_{uuid.uuid4()}"
            })
            
    return opt_id, camp_id

@patch('claude_agent.get_client')
def test_1_successful_feedback_evaluation_improved(mock_get_client):
    # Before: 2 payments out of 10 = 20% conversion, 1000 rev
    # After: 5 payments out of 10 = 50% conversion, 5000 rev -> IMPROVED
    
    opt_id, camp_id = setup_opt_and_campaign()
    
    class MockClient:
        class Chat:
            class Completions:
                def create(self, **kwargs):
                    class MockMsg:
                        content = '{"interpretation": "Great", "possible_explanation": "Good discount", "future_recommendation": "Keep it", "confidence_level": "high"}'
                    class MockChoice:
                        message = MockMsg()
                    class MockResponse:
                        choices = [MockChoice()]
                    return MockResponse()
            completions = Completions()
        chat = Chat()
    
    mock_get_client.return_value = MockClient()
    
    response = client.post(f"/optimizations/{opt_id}/feedback?merchant_id=test_fb_merchant")
    assert response.status_code == 200
    data = response.json()
    assert data["outcome"] == "IMPROVED"
    assert data["changes"]["conversion_rate"] == 30.0 # 50 - 20
    assert data["changes"]["revenue"] == 4000.0 # 5000 - 1000

@patch('claude_agent.get_client')
def test_3_declined_performance(mock_get_client):
    # Before: 2 payments out of 10 = 20% conversion, 1000 rev
    # After: 1 payment out of 10 = 10% conversion, 500 rev -> DECLINED
    opt_id, camp_id = setup_opt_and_campaign(after_offers=10, after_payments=1, after_revenue=500)
    mock_get_client.return_value.chat.completions.create.return_value.choices[0].message.content = '{"interpretation": "Bad", "possible_explanation": "Too low", "future_recommendation": "Stop", "confidence_level": "high"}'
    
    response = client.post(f"/optimizations/{opt_id}/feedback?merchant_id=test_fb_merchant")
    assert response.status_code == 200
    data = response.json()
    assert data["outcome"] == "DECLINED"
    assert data["changes"]["conversion_rate"] == -10.0
    assert data["changes"]["revenue"] == -500.0

@patch('claude_agent.get_client')
def test_4_no_significant_change(mock_get_client):
    # Before: 2 payments out of 10 = 20% conversion, 1000 rev
    # After: exactly same -> 0 change -> NO_SIGNIFICANT_CHANGE
    opt_id, camp_id = setup_opt_and_campaign(after_offers=10, after_payments=2, after_revenue=1000)
    mock_get_client.return_value.chat.completions.create.return_value.choices[0].message.content = '{"interpretation": "Same", "possible_explanation": "No effect", "future_recommendation": "Try else", "confidence_level": "medium"}'
    
    response = client.post(f"/optimizations/{opt_id}/feedback?merchant_id=test_fb_merchant")
    assert response.status_code == 200
    data = response.json()
    assert data["outcome"] == "NO_SIGNIFICANT_CHANGE"
    assert data["changes"]["conversion_rate"] == 0.0
    assert data["changes"]["revenue"] == 0.0

@patch('claude_agent.get_client')
def test_5_insufficient_data(mock_get_client):
    opt_id, camp_id = setup_opt_and_campaign(after_offers=0, after_payments=0, after_revenue=0)
    mock_get_client.return_value.chat.completions.create.return_value.choices[0].message.content = '{"interpretation": "No data", "possible_explanation": "None", "future_recommendation": "Wait", "confidence_level": "low"}'
    
    response = client.post(f"/optimizations/{opt_id}/feedback?merchant_id=test_fb_merchant")
    assert response.status_code == 200
    assert response.json()["outcome"] == "INSUFFICIENT_DATA"

def test_6_optimization_not_found():
    response = client.post(f"/optimizations/fake_opt/feedback?merchant_id=test_fb_merchant")
    assert response.status_code == 400

def test_7_merchant_ownership_failure():
    opt_id, camp_id = setup_opt_and_campaign()
    response = client.post(f"/optimizations/{opt_id}/feedback?merchant_id=wrong_merchant")
    assert response.status_code == 400

def test_8_optimization_not_executed():
    opt_id, camp_id = setup_opt_and_campaign(status="APPROVED")
    response = client.post(f"/optimizations/{opt_id}/feedback?merchant_id=test_fb_merchant")
    assert response.status_code == 400
    assert "Cannot evaluate feedback" in response.json()["detail"]

@patch('claude_agent.get_client')
def test_12_ai_interpretation_failure(mock_get_client):
    opt_id, camp_id = setup_opt_and_campaign()
    
    class ExplodingClient:
        @property
        def chat(self):
            raise Exception("API Down")
            
    mock_get_client.return_value = ExplodingClient()
    
    response = client.post(f"/optimizations/{opt_id}/feedback?merchant_id=test_fb_merchant")
    assert response.status_code == 200
    data = response.json()
    assert data["outcome"] == "IMPROVED" # Deterministic logic still works!
    assert "unavailable" in data["ai_interpretation"]["interpretation"]

@patch('claude_agent.get_client')
def test_14_duplicate_feedback_handling(mock_get_client):
    opt_id, camp_id = setup_opt_and_campaign()
    mock_get_client.return_value.chat.completions.create.return_value.choices[0].message.content = '{"interpretation": "Ok", "possible_explanation": "x", "future_recommendation": "y", "confidence_level": "high"}'
    
    res1 = client.post(f"/optimizations/{opt_id}/feedback?merchant_id=test_fb_merchant")
    assert res1.status_code == 200
    fb_id = res1.json()["feedback_id"]
    
    res2 = client.post(f"/optimizations/{opt_id}/feedback?merchant_id=test_fb_merchant")
    assert res2.status_code == 200
    # Should return same feedback_id (Idempotent)
    assert res2.json()["feedback_id"] == fb_id

