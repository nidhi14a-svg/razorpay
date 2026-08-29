import pytest
from fastapi.testclient import TestClient
from main import app
import database
import uuid
from unittest.mock import patch
from datetime import datetime, timezone

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup: clean specific test data
    database.merchants_collection.delete_many({"merchant_id": "test_hist_merchant"})
    database.merchants_collection.delete_many({"merchant_id": "test_hist_merchant_b"})
    database.campaigns_collection.delete_many({"merchant_id": {"$in": ["test_hist_merchant", "test_hist_merchant_b"]}})
    database.offers_collection.delete_many({"merchant_id": {"$in": ["test_hist_merchant", "test_hist_merchant_b"]}})
    database.orders_collection.delete_many({"merchant_id": {"$in": ["test_hist_merchant", "test_hist_merchant_b"]}})
    
    # Create merchant A
    database.merchants_collection.insert_one({
        "merchant_id": "test_hist_merchant",
        "business_name": "Test Hist Merchant",
        "email": "hist@test.com",
        "password": "pass"
    })
    
    # Create merchant B for isolation testing
    database.merchants_collection.insert_one({
        "merchant_id": "test_hist_merchant_b",
        "business_name": "Test Hist Merchant B",
        "email": "hist_b@test.com",
        "password": "pass"
    })
    
    yield
    
    # Teardown
    database.merchants_collection.delete_many({"merchant_id": "test_hist_merchant"})
    database.merchants_collection.delete_many({"merchant_id": "test_hist_merchant_b"})
    database.campaigns_collection.delete_many({"merchant_id": {"$in": ["test_hist_merchant", "test_hist_merchant_b"]}})
    database.offers_collection.delete_many({"merchant_id": {"$in": ["test_hist_merchant", "test_hist_merchant_b"]}})
    database.orders_collection.delete_many({"merchant_id": {"$in": ["test_hist_merchant", "test_hist_merchant_b"]}})

def test_merchant_with_no_historical_campaigns():
    response = client.get("/merchants/test_hist_merchant/historical-performance")
    assert response.status_code == 200
    data = response.json()
    assert data["merchant_id"] == "test_hist_merchant"
    assert data["total_campaigns"] == 0
    assert data["completed_campaigns"] == 0
    assert data["total_offers"] == 0
    assert data["total_orders"] == 0
    assert data["revenue"] == 0.0

def test_merchant_with_campaigns_and_revenue():
    # Insert a campaign
    camp_id = str(uuid.uuid4())
    database.campaigns_collection.insert_one({
        "campaign_id": camp_id,
        "merchant_id": "test_hist_merchant",
        "status": "COMPLETED",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Insert an offer
    offer_id = str(uuid.uuid4())
    database.offers_collection.insert_one({
        "offer_id": offer_id,
        "merchant_id": "test_hist_merchant",
        "campaign_id": camp_id,
        "customer_id": "cust1",
        "customer_segment": "loyal",
        "discount_percentage": 10.0,
        "status": "PAYMENT_VERIFIED"
    })
    
    # Insert an order (revenue)
    database.orders_collection.insert_one({
        "offer_id": offer_id,
        "merchant_id": "test_hist_merchant",
        "razorpay_order_id": str(uuid.uuid4()),
        "amount": 50000, # 500.00 INR
        "payment_status": "PAYMENT_VERIFIED"
    })
    
    response = client.get("/merchants/test_hist_merchant/historical-performance")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_campaigns"] == 1
    assert data["completed_campaigns"] == 1
    assert data["total_offers"] == 1
    assert data["total_orders"] == 1
    assert data["verified_payments"] == 1
    assert data["revenue"] == 500.0
    assert data["conversion_rate"] == 100.0
    assert data["average_order_value"] == 500.0

def test_segment_level_historical_performance():
    camp_id = str(uuid.uuid4())
    database.campaigns_collection.insert_one({
        "campaign_id": camp_id,
        "merchant_id": "test_hist_merchant",
        "status": "COMPLETED",
    })
    
    # Loyal offer (verified)
    off1 = str(uuid.uuid4())
    database.offers_collection.insert_one({"offer_id": off1, "merchant_id": "test_hist_merchant", "campaign_id": camp_id, "customer_id": "c1", "customer_segment": "loyal"})
    database.orders_collection.insert_one({"offer_id": off1, "merchant_id": "test_hist_merchant", "razorpay_order_id": str(uuid.uuid4()), "amount": 10000, "payment_status": "PAYMENT_VERIFIED"})
    
    # Loyal offer (not verified)
    off2 = str(uuid.uuid4())
    database.offers_collection.insert_one({"offer_id": off2, "merchant_id": "test_hist_merchant", "campaign_id": camp_id, "customer_id": "c2", "customer_segment": "loyal"})
    
    # New visitor offer (verified)
    off3 = str(uuid.uuid4())
    database.offers_collection.insert_one({"offer_id": off3, "merchant_id": "test_hist_merchant", "campaign_id": camp_id, "customer_id": "c3", "customer_segment": "new_visitor"})
    database.orders_collection.insert_one({"offer_id": off3, "merchant_id": "test_hist_merchant", "razorpay_order_id": str(uuid.uuid4()), "amount": 20000, "payment_status": "PAYMENT_VERIFIED"})
    
    response = client.get("/merchants/test_hist_merchant/historical-performance/segments")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 2
    
    loyal_seg = next((s for s in data if s["segment"] == "loyal"), None)
    new_seg = next((s for s in data if s["segment"] == "new_visitor"), None)
    
    assert loyal_seg is not None
    assert loyal_seg["total_offers"] == 2
    assert loyal_seg["verified_payments"] == 1
    assert loyal_seg["conversion_rate"] == 50.0
    assert loyal_seg["revenue"] == 100.0
    
    assert new_seg is not None
    assert new_seg["total_offers"] == 1
    assert new_seg["verified_payments"] == 1
    assert new_seg["conversion_rate"] == 100.0
    assert new_seg["revenue"] == 200.0

def test_merchant_isolation():
    # Merchant A data
    camp_a = str(uuid.uuid4())
    database.campaigns_collection.insert_one({"campaign_id": camp_a, "merchant_id": "test_hist_merchant", "status": "COMPLETED"})
    database.offers_collection.insert_one({"offer_id": str(uuid.uuid4()), "merchant_id": "test_hist_merchant", "campaign_id": camp_a, "customer_id": "c1"})
    
    # Merchant B data
    camp_b = str(uuid.uuid4())
    database.campaigns_collection.insert_one({"campaign_id": camp_b, "merchant_id": "test_hist_merchant_b", "status": "COMPLETED"})
    database.offers_collection.insert_one({"offer_id": str(uuid.uuid4()), "merchant_id": "test_hist_merchant_b", "campaign_id": camp_b, "customer_id": "c2"})
    
    # Check Merchant A
    response_a = client.get("/merchants/test_hist_merchant/historical-performance")
    data_a = response_a.json()
    assert data_a["total_campaigns"] == 1
    assert data_a["total_offers"] == 1
    
    # Check Merchant B
    response_b = client.get("/merchants/test_hist_merchant_b/historical-performance")
    data_b = response_b.json()
    assert data_b["total_campaigns"] == 1
    assert data_b["total_offers"] == 1

@patch("claude_agent.get_client")
def test_ai_context_contains_historical_summary(mock_get_client):
    class MockMessage:
        def __init__(self):
            self.content = '{"recommended_offer_type": "free_shipping", "recommended_discount_percentage": 0, "reason": "test", "confidence": 1.0}'
    
    class MockChoice:
        def __init__(self):
            self.message = MockMessage()
            
    class MockResponse:
        def __init__(self):
            self.choices = [MockChoice()]
            
    class MockCompletions:
        def create(self, **kwargs):
            self.last_kwargs = kwargs
            return MockResponse()
            
    class MockChat:
        def __init__(self):
            self.completions = MockCompletions()
            
    class MockClient:
        def __init__(self):
            self.chat = MockChat()
            
    mock_client_instance = MockClient()
    mock_get_client.return_value = mock_client_instance
    
    # Setup some historical data
    camp_id = str(uuid.uuid4())
    database.campaigns_collection.insert_one({"campaign_id": camp_id, "merchant_id": "test_hist_merchant", "status": "COMPLETED"})
    database.offers_collection.insert_one({"offer_id": str(uuid.uuid4()), "merchant_id": "test_hist_merchant", "campaign_id": camp_id, "customer_id": "c1", "customer_segment": "loyal"})
    
    # Generate offer
    response = client.post("/offers/generate", json={
        "merchant_id": "test_hist_merchant",
        "customer": {
            "id": "c1",
            "purchase_count": 5
        }
    })
    
    assert response.status_code == 200
    
    # Verify the prompt sent to the AI contained historical context
    last_call = mock_client_instance.chat.completions.last_kwargs
    system_prompt = last_call["messages"][0]["content"]
    user_message = last_call["messages"][1]["content"]
    
    assert "Consider historical learning insights if provided" in system_prompt
    assert "Merchant Historical Performance:" in user_message
    
    # Check if the summary string is in the prompt
    # The expected summary includes overall_completed_campaigns
    assert "overall_completed_campaigns" in user_message
