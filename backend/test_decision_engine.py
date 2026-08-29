import sys
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app
client = TestClient(app)

class TestOfferRecommendationFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        self.patcher_merchants = patch('main.merchants_collection.find_one')
        self.mock_merchant_find = self.patcher_merchants.start()
        self.mock_merchant_find.return_value = {
            "merchant_id": "test_merchant_123",
            "rules": {
                "max_discount_percentage": 20.0,
                "min_margin_percentage": 30.0
            }
        }
        
        self.patcher_customers = patch('main.customers_collection.find_one')
        self.mock_customer_find = self.patcher_customers.start()
        self.mock_customer_find.return_value = None

        self.patcher_campaigns = patch('main.campaigns_collection.find_one')
        self.mock_campaigns_find = self.patcher_campaigns.start()
        self.mock_campaigns_find.return_value = {
            "campaign_name": "Test Campaign",
            "target_segment": "All"
        }
        
        self.patcher_historical = patch('decision_engine.get_merchant_historical_performance')
        self.mock_hist = self.patcher_historical.start()
        self.mock_hist.return_value = {"total_campaigns": 1, "conversion_rate": 0.05}
        
        self.patcher_segment_hist = patch('decision_engine.get_merchant_segment_performance')
        self.mock_seg_hist = self.patcher_segment_hist.start()
        self.mock_seg_hist.return_value = []

        self.patcher_agent = patch('claude_agent.get_offer_for_segment')
        self.mock_agent = self.patcher_agent.start()

    def tearDown(self):
        self.patcher_merchants.stop()
        self.patcher_customers.stop()
        self.patcher_campaigns.stop()
        self.patcher_historical.stop()
        self.patcher_segment_hist.stop()
        self.patcher_agent.stop()

    def send_recommendation(self, customer_data, campaign_id=None):
        payload = {
            "merchant_id": "test_merchant_123",
            "customer": customer_data
        }
        if campaign_id:
            payload["campaign_id"] = campaign_id
        return client.post("/offers/recommend", json=payload)

    # Base Segment Tests (1-7)
    def test_1_loyal_customer_recommendation(self):
        self.mock_agent.return_value = {"reason": "Free priority shipping", "recommended_discount_percentage": 0, "recommended_offer_type": "free_shipping", "confidence": 0.9}
        resp = self.send_recommendation({"purchase_count": 5, "days_since_last_purchase": 10})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["segment"], "loyal")
        self.assertEqual(data["guardrail_status"], "APPROVED")

    def test_2_new_visitor_recommendation(self):
        self.mock_agent.return_value = {"reason": "10% off", "recommended_discount_percentage": 10, "recommended_offer_type": "percentage_discount", "confidence": 0.8}
        resp = self.send_recommendation({"purchase_count": 0, "cart_status": "browsing"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["segment"], "new_visitor")
        self.assertEqual(resp.json()["guardrail_status"], "APPROVED")

    def test_3_cart_abandoned_recommendation(self):
        self.mock_agent.return_value = {"reason": "5% off", "recommended_discount_percentage": 5, "recommended_offer_type": "percentage_discount", "confidence": 0.9}
        resp = self.send_recommendation({"cart_status": "abandoned", "days_since_last_purchase": 0})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["segment"], "cart_abandoned")

    def test_4_high_value_customer(self):
        self.mock_agent.return_value = {"reason": "Premium Service", "recommended_discount_percentage": 0, "recommended_offer_type": "premium_upgrade", "confidence": 0.95}
        resp = self.send_recommendation({"lifetime_value": 15000})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["segment"], "high_value")

    def test_5_price_sensitive_customer(self):
        self.mock_agent.return_value = {"reason": "15% off", "recommended_discount_percentage": 15, "recommended_offer_type": "percentage_discount", "confidence": 0.85}
        resp = self.send_recommendation({"average_order_value": 1500})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["segment"], "price_sensitive")

    def test_6_dormant_customer(self):
        self.mock_agent.return_value = {"reason": "20% off", "recommended_discount_percentage": 20, "recommended_offer_type": "percentage_discount", "confidence": 0.75}
        resp = self.send_recommendation({"days_since_last_purchase": 100})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["segment"], "dormant")

    def test_7_regular_customer(self):
        self.mock_agent.return_value = {"reason": "5% points", "recommended_discount_percentage": 5, "recommended_offer_type": "loyalty_points", "confidence": 0.8}
        resp = self.send_recommendation({"purchase_count": 1, "days_since_last_purchase": 45})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["segment"], "regular")

    # Edge cases and validation (8-20)
    def test_8_ai_valid_discount(self):
        self.mock_agent.return_value = {"reason": "Valid", "recommended_discount_percentage": 15, "recommended_offer_type": "percentage_discount", "confidence": 0.9}
        resp = self.send_recommendation({"purchase_count": 0})
        self.assertEqual(resp.json()["guardrail_status"], "APPROVED")
        self.assertEqual(resp.json()["recommended_discount_percentage"], 15.0)

    def test_9_ai_discount_above_merchant_maximum(self):
        self.mock_agent.return_value = {"reason": "Too high", "recommended_discount_percentage": 30, "recommended_offer_type": "percentage_discount", "confidence": 0.9}
        resp = self.send_recommendation({"purchase_count": 0})
        self.assertEqual(resp.json()["guardrail_status"], "REJECTED_BY_GUARDRAILS")

    def test_10_ai_negative_discount(self):
        self.mock_agent.return_value = {"reason": "Negative", "recommended_discount_percentage": -5, "recommended_offer_type": "percentage_discount", "confidence": 0.9}
        resp = self.send_recommendation({"purchase_count": 0})
        self.assertEqual(resp.json()["guardrail_status"], "ERROR_NEGATIVE_DISCOUNT")

    def test_11_ai_malformed_json(self):
        self.mock_agent.return_value = "This is a raw string, not a dict"
        resp = self.send_recommendation({"purchase_count": 0})
        self.assertEqual(resp.json()["guardrail_status"], "ERROR_MALFORMED_JSON")
        
        self.mock_agent.return_value = {"reason": "No discount field"}
        resp = self.send_recommendation({"purchase_count": 0})
        self.assertEqual(resp.json()["guardrail_status"], "ERROR_MISSING_DISCOUNT")

    def test_12_ai_invalid_confidence(self):
        self.mock_agent.return_value = {"reason": "Valid", "recommended_discount_percentage": 10, "recommended_offer_type": "percentage_discount", "confidence": 1.5}
        resp = self.send_recommendation({"purchase_count": 0})
        self.assertEqual(resp.json()["guardrail_status"], "ERROR_INVALID_CONFIDENCE")
        
        self.mock_agent.return_value = {"reason": "Valid", "recommended_discount_percentage": 10, "recommended_offer_type": "percentage_discount", "confidence": -0.1}
        resp = self.send_recommendation({"purchase_count": 0})
        self.assertEqual(resp.json()["guardrail_status"], "ERROR_INVALID_CONFIDENCE")

    def test_13_openrouter_failure(self):
        self.mock_agent.side_effect = Exception("OpenRouter Down")
        resp = self.send_recommendation({"purchase_count": 0})
        self.assertEqual(resp.status_code, 200) # Endpoint shouldn't 500, it should safely return error status
        self.assertEqual(resp.json()["guardrail_status"], "ERROR_AI_FAILURE")

    def test_14_merchant_not_found(self):
        self.mock_merchant_find.return_value = None
        resp = self.send_recommendation({"purchase_count": 0})
        self.assertEqual(resp.status_code, 404)

    def test_15_customer_not_found(self):
        # We only hit not found if they supply ID and we can't find it
        self.mock_customer_find.return_value = None
        payload = {"merchant_id": "test_merchant_123", "customer": {"id": "nonexistent"}}
        resp = client.post("/offers/recommend", json=payload)
        self.assertEqual(resp.status_code, 404)

    def test_16_campaign_not_found(self):
        self.mock_campaigns_find.return_value = None
        resp = self.send_recommendation({"purchase_count": 0}, campaign_id="invalid")
        self.assertEqual(resp.status_code, 404)

    def test_17_unauthorized_merchant_access(self):
        # Implicitly handled if merchant_id mismatch on campaign retrieval
        self.mock_campaigns_find.return_value = None # merchant mismatch behaves like not found
        resp = self.send_recommendation({"purchase_count": 0}, campaign_id="camp123")
        self.assertEqual(resp.status_code, 404)

    def test_18_historical_data_unavailable(self):
        self.mock_hist.return_value = None
        self.mock_seg_hist.return_value = None
        self.mock_agent.return_value = {"reason": "Valid", "recommended_discount_percentage": 10, "recommended_offer_type": "percentage_discount", "confidence": 0.9}
        resp = self.send_recommendation({"purchase_count": 0})
        self.assertEqual(resp.json()["guardrail_status"], "APPROVED")

    def test_19_guardrail_rejection(self):
        # Rejecting a loyal customer getting a big discount
        self.mock_agent.return_value = {"reason": "Loyalty 15% off", "recommended_discount_percentage": 15, "recommended_offer_type": "percentage_discount", "confidence": 0.9}
        resp = self.send_recommendation({"purchase_count": 5, "days_since_last_purchase": 10})
        self.assertEqual(resp.json()["guardrail_status"], "REJECTED_BY_GUARDRAILS")

    def test_20_successful_guardrail_approval(self):
        self.mock_agent.return_value = {"reason": "Safe 10% off", "recommended_discount_percentage": 10, "recommended_offer_type": "percentage_discount", "confidence": 0.9}
        resp = self.send_recommendation({"purchase_count": 0})
        self.assertEqual(resp.json()["guardrail_status"], "APPROVED")
        self.assertEqual(resp.json()["recommended_offer_type"], "percentage_discount")

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    unittest.main()
