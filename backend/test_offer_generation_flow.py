import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
client = TestClient(app)

class TestOfferGenerationFlow(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Create a mock merchant in the DB to avoid setting up a real one, or patch find_one
        pass
        
    def setUp(self):
        # Patch the merchants_collection and offers_collection
        self.patcher_merchants = patch('main.merchants_collection.find_one')
        self.mock_merchant_find = self.patcher_merchants.start()
        self.mock_merchant_find.return_value = {
            "merchant_id": "test_merchant_123",
            "rules": {
                "max_discount_percentage": 20.0,
                "min_margin_percentage": 30.0
            }
        }
        
        self.patcher_offers = patch('main.offers_collection.insert_one')
        self.mock_offer_insert = self.patcher_offers.start()
        
        # Patch the claude_agent API call
        self.patcher_agent = patch('claude_agent.get_offer_for_segment')
        self.mock_agent = self.patcher_agent.start()

    def tearDown(self):
        self.patcher_merchants.stop()
        self.patcher_offers.stop()
        self.patcher_agent.stop()

    def test_merchant_not_found(self):
        """Test that missing merchant returns 404"""
        self.mock_merchant_find.return_value = None
        
        response = client.post("/offers/generate", json={
            "merchant_id": "invalid_merchant",
            "customer": {"purchase_count": 0}
        })
        self.assertEqual(response.status_code, 404)
        self.mock_agent.assert_not_called()

    def test_loyal_customer_flow(self):
        """Test valid customer -> segment -> offer generated and stored"""
        self.mock_agent.return_value = {
            "reason": "Free priority shipping",
            "recommended_offer_type": "percentage_discount", "confidence": 1.0, "recommended_discount_percentage": 0
        }
        
        response = client.post("/offers/generate", json={
            "merchant_id": "test_merchant_123",
            "customer": {"purchase_count": 5, "days_since_last_purchase": 10}
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["segment"], "loyal")
        self.assertEqual(data["discount_percentage"], 0.0)
        self.assertEqual(data["offer_details"], "Free priority shipping")
        self.assertIn("offer_id", data)
        
        # Verify it was stored
        self.mock_offer_insert.assert_called_once()
        stored_doc = self.mock_offer_insert.call_args[0][0]
        self.assertEqual(stored_doc["customer_segment"], "loyal")
        self.assertEqual(stored_doc["discount_percentage"], 0.0)

    def test_new_visitor_flow(self):
        """Test new visitor -> 10% discount -> stored"""
        self.mock_agent.return_value = {
            "reason": "10% off first purchase",
            "recommended_offer_type": "percentage_discount", "confidence": 1.0, "recommended_discount_percentage": 10
        }
        
        response = client.post("/offers/generate", json={
            "merchant_id": "test_merchant_123",
            "customer": {"purchase_count": 0, "cart_status": "browsing"}
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["segment"], "new_visitor")
        self.assertEqual(data["discount_percentage"], 10.0)
        
        # Verify it was stored
        self.mock_offer_insert.assert_called_once()

    def test_cart_abandoned_flow(self):
        """Test cart abandoned -> segment -> offer generated"""
        self.mock_agent.return_value = {
            "reason": "₹200 instant coupon",
            "recommended_offer_type": "percentage_discount", "confidence": 1.0, "recommended_discount_percentage": 5
        }
        
        response = client.post("/offers/generate", json={
            "merchant_id": "test_merchant_123",
            "customer": {"cart_status": "abandoned", "days_since_last_purchase": 0}
        })
        
        if response.status_code != 200:
            print(response.json())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["segment"], "cart_abandoned")

    def test_ai_generation_failure(self):
        """Test AI failure correctly propagates 500 error"""
        self.mock_agent.side_effect = Exception("OpenRouter API Down")
        
        response = client.post("/offers/generate", json={
            "merchant_id": "test_merchant_123",
            "customer": {"purchase_count": 0}
        })
        
        self.assertEqual(response.status_code, 500)
        self.mock_offer_insert.assert_not_called()

    def test_ai_excessive_discount_fallback(self):
        """Test AI returning excessive discount triggers fallback logic (or 400 if completely fails)"""
        # We mock get_offer_for_segment. In main.py, it's called first with use_deterministic=False, then True
        def mock_ai_call(segment, rules, use_deterministic, **kwargs):
            if not use_deterministic:
                # Return invalid excessive discount
                return {"reason": "Crazy 90% off!!", "recommended_offer_type": "percentage_discount", "confidence": 1.0, "recommended_discount_percentage": 90}
            else:
                # Fallback returns safe discount
                return {"reason": "Safe 10% off", "recommended_offer_type": "percentage_discount", "confidence": 1.0, "recommended_discount_percentage": 10}
                
        self.mock_agent.side_effect = mock_ai_call
        
        response = client.post("/offers/generate", json={
            "merchant_id": "test_merchant_123",
            "customer": {"purchase_count": 0} # new visitor
        })
        
        # Should succeed because it fell back to deterministic
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["discount_percentage"], 10.0)
        self.assertEqual(data["offer_details"], "Safe 10% off")
        
        # Verify the mock was called twice (once for AI, once for fallback)
        self.assertEqual(self.mock_agent.call_count, 2)

    def test_invalid_customer_data(self):
        """Test API gracefully rejects invalid schema"""
        response = client.post("/offers/generate", json={
            "merchant_id": "test_merchant_123",
            "customer": "this should be a dict"
        })
        self.assertEqual(response.status_code, 422)

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    unittest.main()
