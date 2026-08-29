import unittest
from unittest.mock import patch, MagicMock
from claude_agent import get_offer_for_segment
from decision_engine import run_offer_decision_engine
from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

class TestPersonalizedOfferGeneration(unittest.TestCase):

    def setUp(self):
        self.merchant_rules = {
            "max_discount_percentage": 20.0,
            "min_margin_percentage": 30.0
        }
        
        # Test stats mocks
        self.new_visitor_stats = {
            "segment_name": "new_visitor",
            "customer_count": 5,
            "average_lifetime_value": 0,
            "average_purchase_count": 0,
            "cart_abandoned_count": 0
        }
        
        self.cart_abandoned_stats = {
            "segment_name": "cart_abandoned",
            "customer_count": 3,
            "average_lifetime_value": 500,
            "average_purchase_count": 1,
            "cart_abandoned_count": 3
        }
        
        self.loyal_stats = {
            "segment_name": "loyal",
            "customer_count": 10,
            "average_lifetime_value": 5000,
            "average_purchase_count": 8,
            "cart_abandoned_count": 1
        }

    # Test 1: new_visitor campaign produces an offer appropriate for new visitors
    @patch('claude_agent.get_client')
    def test_new_visitor_offer(self, mock_get_client):
        # Mock OpenRouter response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"segment": "new_visitor", "offer": "Welcome 10% Off", "discount_pct": 10, "reason": "Acquire new customer", "priority": "high"}'
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        result = run_offer_decision_engine("demo_merchant", "new_visitor", self.new_visitor_stats, self.merchant_rules)
        self.assertEqual(result["discount_percentage"], 10.0)
        self.assertEqual(result["segment"], "new_visitor")
        self.assertIn("Welcome", result["offer_details"])

    # Test 2: cart_abandoned campaign produces an offer appropriate for abandoned carts
    @patch('claude_agent.get_client')
    def test_cart_abandoned_offer(self, mock_get_client):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"segment": "cart_abandoned", "offer": "Finish your checkout with 5% off", "discount_pct": 5, "reason": "Recover cart", "priority": "high"}'
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        result = run_offer_decision_engine("demo_merchant", "cart_abandoned", self.cart_abandoned_stats, self.merchant_rules)
        self.assertEqual(result["discount_percentage"], 5.0)

    # Test 3: loyal campaign produces an offer appropriate for loyal customers (NO discount)
    @patch('claude_agent.get_client')
    def test_loyal_offer(self, mock_get_client):
        mock_response = MagicMock()
        # AI hallucinating a discount for loyal customer
        mock_response.choices[0].message.content = '{"segment": "loyal", "offer": "Loyalty 15% Off", "discount_pct": 15, "reason": "Reward them", "priority": "low"}'
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        # Engine should detect this violates loyal customer guardrail (purchase_count > 3 -> max 5%)
        # and fallback to deterministic which gives 0% discount
        result = run_offer_decision_engine("demo_merchant", "loyal", self.loyal_stats, self.merchant_rules)
        self.assertEqual(result["discount_percentage"], 0.0)

    # Test 4: AI discount never exceeds merchant max_discount_percentage
    @patch('claude_agent.get_client')
    def test_max_discount_guardrail(self, mock_get_client):
        mock_response = MagicMock()
        # AI hallucinating a 30% discount when max is 20%
        mock_response.choices[0].message.content = '{"segment": "new_visitor", "offer": "Crazy 30% Off", "discount_pct": 30, "reason": "Aggressive acquisition", "priority": "high"}'
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        result = run_offer_decision_engine("demo_merchant", "new_visitor", self.new_visitor_stats, self.merchant_rules)
        # Should fallback to deterministic for new_visitor, which is 10%
        self.assertEqual(result["discount_percentage"], 10.0)

    # Test 5: Malformed LLM JSON is handled safely
    @patch('claude_agent.get_client')
    def test_malformed_json_fallback(self, mock_get_client):
        mock_response = MagicMock()
        # Invalid JSON missing quotes
        mock_response.choices[0].message.content = 'Here is the offer: {segment: new_visitor, discount: 10}'
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        result = run_offer_decision_engine("demo_merchant", "new_visitor", self.new_visitor_stats, self.merchant_rules)
        # Should cleanly parse using fallback logic and extract 10.0 discount
        self.assertEqual(result["discount_percentage"], 10.0)

    # Test 6: Missing optional customer data does not crash the system
    @patch('claude_agent.get_client')
    def test_missing_customer_data(self, mock_get_client):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"segment": "unknown", "offer": "Generic 5% Off", "discount_pct": 5}'
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        # Send empty stats
        empty_stats = {}
        result = run_offer_decision_engine("demo_merchant", "unknown", empty_stats, self.merchant_rules)
        self.assertEqual(result["discount_percentage"], 5.0)

    # Test 7 & 8: Multiple target segments produce multiple offers & existing flow works
    # This is tested implicitly by testing the POST /campaigns endpoint
    @patch('main.customers_collection')
    @patch('decision_engine.run_offer_decision_engine')
    def test_campaign_creation_flow(self, mock_run_engine, mock_customers):
        # Mock the engine to return different offers based on segment
        def side_effect(merchant_id, segment, segment_stats, merchant_rules, campaign_context=None):
            if segment == "loyal":
                return {"segment": "loyal", "offer_details": "Free Shipping", "discount_percentage": 0, "explanation": "Rule"}
            return {"segment": segment, "offer_details": "10% off", "discount_percentage": 10, "explanation": "Rule"}
            
        mock_run_engine.side_effect = side_effect
        
        # Provide customers in two different segments
        mock_customers.find.return_value = [
            {"id": "c1", "merchant_id": "demo_merchant_001", "purchase_count": 5, "days_since_last_purchase": 10}, # loyal
            {"id": "c2", "merchant_id": "demo_merchant_001", "purchase_count": 0, "cart_status": "browsing"} # new_visitor
        ]
        
        import uuid
        payload = {
            "merchant_id": "demo_merchant_001",
            "campaign_name": f"Test Multiple Segments {uuid.uuid4()}",
            "target_segment": "all"
        }
        
        response = client.post("/campaigns", json=payload)
        data = response.json()
        print(f"API RESPONSE: {data}")
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(data["status"], "ACTIVE")
        self.assertGreater(len(data["offers"]), 1)
        self.assertIn("loyal", data["offers"])
        self.assertEqual(data["offers"]["loyal"]["discount_pct"], 0)

if __name__ == '__main__':
    unittest.main()
