import pytest
from fastapi.testclient import TestClient
import uuid
from unittest.mock import patch

from main import app
from database import campaigns_collection, merchants_collection, offers_collection, orders_collection, optimizations_collection
from optimization_agent import analyze_campaign_for_optimization

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    merchants_collection.delete_many({"merchant_id": {"$regex": "^test_opt_"}})
    campaigns_collection.delete_many({"merchant_id": {"$regex": "^test_opt_"}})
    offers_collection.delete_many({"merchant_id": {"$regex": "^test_opt_"}})
    orders_collection.delete_many({"merchant_id": {"$regex": "^test_opt_"}})
    optimizations_collection.delete_many({"merchant_id": {"$regex": "^test_opt_"}})
    
    merchants_collection.insert_one({
        "merchant_id": "test_opt_merchant",
        "rules": {
            "max_discount_percentage": 20.0,
            "min_margin_percentage": 30.0
        }
    })
    
    yield
    
    merchants_collection.delete_many({"merchant_id": {"$regex": "^test_opt_"}})
    campaigns_collection.delete_many({"merchant_id": {"$regex": "^test_opt_"}})
    offers_collection.delete_many({"merchant_id": {"$regex": "^test_opt_"}})
    orders_collection.delete_many({"merchant_id": {"$regex": "^test_opt_"}})
    optimizations_collection.delete_many({"merchant_id": {"$regex": "^test_opt_"}})


class MockMessage:
    def __init__(self, content):
        self.content = content

class MockChoice:
    def __init__(self, content):
        self.message = MockMessage(content)
        
class MockResponse:
    def __init__(self, content):
        self.choices = [MockChoice(content)]

class MockCompletions:
    def __init__(self, content):
        self.content = content
    def create(self, **kwargs):
        return MockResponse(self.content)
        
class MockChat:
    def __init__(self, content):
        self.completions = MockCompletions(content)
        
class MockClient:
    def __init__(self, content):
        self.chat = MockChat(content)


def setup_campaign(offers_count, payments_count, amount=100000):
    camp_id = f"test_opt_camp_{uuid.uuid4()}"
    campaigns_collection.insert_one({
        "campaign_id": camp_id,
        "merchant_id": "test_opt_merchant",
        "campaign_name": "Test Campaign",
        "status": "COMPLETED"
    })
    
    for i in range(offers_count):
        offer_id = f"offer_{uuid.uuid4()}"
        offers_collection.insert_one({
            "offer_id": offer_id,
            "merchant_id": "test_opt_merchant",
            "campaign_id": camp_id,
            "customer_id": f"cust_{i}",
            "customer_segment": "new_visitor"
        })
        
        if i < payments_count:
            orders_collection.insert_one({
                "offer_id": offer_id,
                "merchant_id": "test_opt_merchant",
                "payment_status": "PAYMENT_VERIFIED",
                "amount": amount,
                "razorpay_order_id": f"order_{uuid.uuid4()}"
            })
            
    return camp_id


@patch('claude_agent.get_client')
def test_1_high_performing_campaign(mock_get_client):
    camp_id = setup_campaign(10, 8)
    
    mock_get_client.return_value = MockClient('{"overall_assessment": "Great!", "recommendations": [{"type": "discount_adjustment", "segment": "new_visitor", "recommended_change": "Maintain discount", "reason": "High conversion", "priority": "low"}]}')
    
    response = client.post(f"/campaigns/{camp_id}/optimize?merchant_id=test_opt_merchant")
    assert response.status_code == 200
    assert response.json()["overall_assessment"] == "Great!"

@patch('claude_agent.get_client')
def test_2_low_performing_campaign(mock_get_client):
    camp_id = setup_campaign(100, 1)
    
    mock_get_client.return_value = MockClient('{"overall_assessment": "Poor performance.", "recommendations": [{"type": "segment_targeting", "segment": "loyal", "recommended_change": "Shift to loyal", "reason": "Low conversion", "priority": "high"}]}')
    
    response = client.post(f"/campaigns/{camp_id}/optimize?merchant_id=test_opt_merchant")
    assert response.status_code == 200

@patch('claude_agent.get_client')
def test_3_campaign_with_no_payments(mock_get_client):
    camp_id = setup_campaign(10, 0)
    
    mock_get_client.return_value = MockClient('{"overall_assessment": "No conversions.", "recommendations": [{"type": "discount_adjustment", "segment": "new_visitor", "recommended_change": "Increase discount to 10%", "reason": "Zero conversion", "priority": "high"}]}')
    
    response = client.post(f"/campaigns/{camp_id}/optimize?merchant_id=test_opt_merchant")
    assert response.status_code == 200

@patch('claude_agent.get_client')
def test_4_campaign_with_no_offers(mock_get_client):
    camp_id = setup_campaign(0, 0)
    
    mock_get_client.return_value = MockClient('{"overall_assessment": "No offers sent.", "recommendations": []}')
    
    response = client.post(f"/campaigns/{camp_id}/optimize?merchant_id=test_opt_merchant")
    assert response.status_code == 200

@patch('claude_agent.get_client')
def test_5_campaign_with_multiple_segments(mock_get_client):
    camp_id = setup_campaign(10, 5)
    
    offers_collection.insert_one({
        "offer_id": f"offer_{uuid.uuid4()}",
        "merchant_id": "test_opt_merchant",
        "campaign_id": camp_id,
        "customer_segment": "loyal"
    })
    
    mock_get_client.return_value = MockClient('{"overall_assessment": "Multiple segments analyzed.", "recommendations": []}')
    
    response = client.post(f"/campaigns/{camp_id}/optimize?merchant_id=test_opt_merchant")
    assert response.status_code == 200

@patch('claude_agent.get_client')
def test_6_insufficient_historical_data(mock_get_client):
    camp_id = setup_campaign(5, 1)
    
    mock_get_client.return_value = MockClient('{"overall_assessment": "Cold start.", "recommendations": []}')
    
    response = client.post(f"/campaigns/{camp_id}/optimize?merchant_id=test_opt_merchant")
    assert response.status_code == 200

@patch('claude_agent.get_client')
def test_7_valid_recommendation_within_rules(mock_get_client):
    camp_id = setup_campaign(10, 5)
    
    # 15% is within max_discount 20%
    mock_get_client.return_value = MockClient('{"overall_assessment": "Valid", "recommendations": [{"type": "discount_adjustment", "segment": "new_visitor", "recommended_change": "Increase to 15%", "reason": "Test", "priority": "high"}]}')
    
    response = client.post(f"/campaigns/{camp_id}/optimize?merchant_id=test_opt_merchant")
    assert response.status_code == 200
    recs = response.json()["recommendations"]
    assert recs[0]["status"] == "GENERATED"

@patch('claude_agent.get_client')
def test_8_violating_max_discount(mock_get_client):
    camp_id = setup_campaign(10, 5)
    
    # 25% violates max_discount 20%
    mock_get_client.return_value = MockClient('{"overall_assessment": "Violation", "recommendations": [{"type": "discount_adjustment", "segment": "new_visitor", "recommended_change": "Increase to 25%", "reason": "Test", "priority": "high"}]}')
    
    response = client.post(f"/campaigns/{camp_id}/optimize?merchant_id=test_opt_merchant")
    assert response.status_code == 200
    recs = response.json()["recommendations"]
    assert recs[0]["status"] == "REJECTED_BY_GUARDRAIL"
    assert "exceeds merchant safe limit" in recs[0]["reason"]

@patch('claude_agent.get_client')
def test_9_violating_minimum_margin(mock_get_client):
    # For min margin 30%, assuming max safe discount is < 20% because of margin constraints
    # Our mocked optimization.py gives max_safe_discount = 28.57% for min_margin_percentage=30
    # Wait, 1 - (30/100) = 0.7. min_price = 2500 / 0.7 = 3571.4. max_discount = 1 - (3571.4/5000) = 28.5%.
    # Let's change the merchant rules in DB to force a low max_safe_discount.
    merchants_collection.update_one({"merchant_id": "test_opt_merchant"}, {"$set": {"rules.min_margin_percentage": 50.0}})
    # min_price = 2500 / (1 - 0.5) = 5000. Max discount = 0%.
    
    camp_id = setup_campaign(10, 5)
    
    # Any discount > 0% should violate margin
    mock_get_client.return_value = MockClient('{"overall_assessment": "Margin violation", "recommendations": [{"type": "discount_adjustment", "segment": "new_visitor", "recommended_change": "Give 5% off", "reason": "Test", "priority": "high"}]}')
    
    response = client.post(f"/campaigns/{camp_id}/optimize?merchant_id=test_opt_merchant")
    assert response.status_code == 200
    recs = response.json()["recommendations"]
    assert recs[0]["status"] == "REJECTED_BY_GUARDRAIL"

@patch('claude_agent.get_client')
def test_10_invalid_segment(mock_get_client):
    camp_id = setup_campaign(10, 5)
    
    mock_get_client.return_value = MockClient('{"overall_assessment": "Invalid segment", "recommendations": [{"type": "audience_expansion", "segment": "fake_segment", "recommended_change": "Target fake segment", "reason": "Test", "priority": "high"}]}')
    
    response = client.post(f"/campaigns/{camp_id}/optimize?merchant_id=test_opt_merchant")
    assert response.status_code == 200
    recs = response.json()["recommendations"]
    assert recs[0]["status"] == "REJECTED_BY_GUARDRAIL"
    assert "Invalid segment" in recs[0]["reason"]

@patch('claude_agent.get_client')
def test_11_openrouter_failure(mock_get_client):
    camp_id = setup_campaign(10, 5)
    
    # Force exception
    class ExplodingClient:
        @property
        def chat(self):
            raise Exception("API Down")
            
    mock_get_client.return_value = ExplodingClient()
    
    response = client.post(f"/campaigns/{camp_id}/optimize?merchant_id=test_opt_merchant")
    assert response.status_code == 200
    assert "Analysis failed due to API unavailability" in response.json()["overall_assessment"]

@patch('claude_agent.get_client')
def test_12_malformed_ai_response(mock_get_client):
    camp_id = setup_campaign(10, 5)
    
    mock_get_client.return_value = MockClient('This is not JSON')
    
    response = client.post(f"/campaigns/{camp_id}/optimize?merchant_id=test_opt_merchant")
    assert response.status_code == 200
    assert "Analysis failed due to API unavailability" in response.json()["overall_assessment"]

def test_13_merchant_not_found():
    response = client.post(f"/campaigns/fake_camp/optimize?merchant_id=fake_merchant")
    assert response.status_code == 404
    assert "Merchant not found" in response.json()["detail"] or "Campaign not found" in response.json()["detail"]

def test_14_unauthorized_merchant():
    camp_id = setup_campaign(1, 1)
    
    # Try to access with different merchant
    merchants_collection.insert_one({"merchant_id": "test_other_merchant"})
    response = client.post(f"/campaigns/{camp_id}/optimize?merchant_id=test_other_merchant")
    assert response.status_code == 404
    
    merchants_collection.delete_one({"merchant_id": "test_other_merchant"})

def test_15_campaign_not_found():
    response = client.post(f"/campaigns/missing_camp/optimize?merchant_id=test_opt_merchant")
    assert response.status_code == 404
    assert "Campaign not found" in response.json()["detail"]

@patch('claude_agent.get_client')
def test_16_optimization_persistence(mock_get_client):
    camp_id = setup_campaign(10, 5)
    
    mock_get_client.return_value = MockClient('{"overall_assessment": "Persistent", "recommendations": []}')
    
    response = client.post(f"/campaigns/{camp_id}/optimize?merchant_id=test_opt_merchant")
    assert response.status_code == 200
    
    opt_id = response.json()["optimization_id"]
    
    # Check DB
    doc = optimizations_collection.find_one({"optimization_id": opt_id})
    assert doc is not None
    assert doc["campaign_id"] == camp_id
    assert "campaign_metrics_snapshot" in doc
    assert doc["overall_assessment"] == "Persistent"

