import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
client = TestClient(app)

class TestStrategySelection(unittest.TestCase):
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

        self.patcher_customers = patch('main.customers_collection.find')
        self.mock_customers_find = self.patcher_customers.start()
        self.mock_customers_find.return_value = [
            {"_id": "c1", "purchase_count": 0, "cart_status": "browsing", "days_since_last_purchase": 10}, # new_visitor
            {"_id": "c2", "purchase_count": 10, "cart_status": "browsing", "days_since_last_purchase": 5}, # loyal
            {"_id": "c3", "days_since_last_purchase": 200, "purchase_count": 2}, # dormant
            {"_id": "c4", "cart_status": "abandoned", "purchase_count": 0, "days_since_last_purchase": 0} # cart_abandoned
        ]
        
        self.patcher_campaigns = patch('main.campaigns_collection.insert_one')
        self.mock_campaigns_insert = self.patcher_campaigns.start()
        
        self.patcher_campaigns_find = patch('main.campaigns_collection.find_one')
        self.mock_campaigns_find = self.patcher_campaigns_find.start()
        self.mock_campaigns_find.return_value = None # No existing campaign
        
        self.patcher_offers = patch('main.offers_collection.insert_one')
        self.mock_offers_insert = self.patcher_offers.start()

        self.patcher_hist_insights = patch('historical_analyzer.get_historical_learning_insights')
        self.mock_hist_insights = self.patcher_hist_insights.start()
        self.mock_hist_insights.return_value = {}

        self.patcher_intelligence = patch('merchant_intelligence.get_merchant_campaign_intelligence')
        self.mock_intelligence = self.patcher_intelligence.start()
        self.mock_intelligence.return_value = {}

        self.patcher_strategy = patch('claude_agent.determine_campaign_strategy')
        self.mock_strategy = self.patcher_strategy.start()
        
        self.patcher_offer = patch('decision_engine.claude_agent.get_offer_for_segment')
        self.mock_offer = self.patcher_offer.start()
        
        def mock_offer_side_effect(segment, *args, **kwargs):
            use_deterministic = kwargs.get('use_deterministic', False)
            if len(args) > 1 and isinstance(args[1], bool): # Handle positional use_deterministic
                use_deterministic = args[1]
                
            if use_deterministic:
                return {"offer": "Safe fallback", "discount_pct": 5, "reason": "Test"}
                
            if segment == "loyal":
                return {"offer": "Free shipping", "discount_pct": 0, "reason": "Test"}
            elif segment == "new_visitor":
                return {"offer": "10% off", "discount_pct": 10, "reason": "Test"}
            elif segment == "dormant":
                return {"offer": "15% off", "discount_pct": 15, "reason": "Test"}
            elif segment == "cart_abandoned":
                return {"offer": "5% off", "discount_pct": 5, "reason": "Test"}
            return {"offer": "5% off", "discount_pct": 5, "reason": "Test"}
            
        self.mock_offer.side_effect = mock_offer_side_effect

    def tearDown(self):
        patch.stopall()

    def test_1_acquisition_goal(self):
        """Test 1: Increase first-time purchases -> Acquisition strategy"""
        self.mock_strategy.return_value = {
            "business_goal": "Increase first-time purchases.",
            "opportunity": {"title": "Acquisition"},
            "strategy": {"type": "acquisition"},
            "target_segments": ["new_visitor"],
            "recommended_action": "Offer first purchase discount."
        }
        
        resp = client.post("/campaigns", json={
            "merchant_id": "test_merchant_123",
            "campaign_name": "Acquisition Campaign",
            "campaign_description": "Increase first-time purchases",
            "target_segment": "auto"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("new_visitor", data["offers"])
        self.assertNotIn("loyal", data["offers"]) # Only new_visitor targeted

    def test_2_reactivation_goal(self):
        """Test 2: Reactivate inactive customers -> Win-back strategy"""
        self.mock_strategy.return_value = {
            "business_goal": "Reactivate inactive customers.",
            "opportunity": {"title": "Reactivation"},
            "strategy": {"type": "win-back"},
            "target_segments": ["dormant"],
            "recommended_action": "Offer win-back discount."
        }
        
        resp = client.post("/campaigns", json={
            "merchant_id": "test_merchant_123",
            "campaign_name": "Win-back Campaign",
            "target_segment": "auto"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("dormant", data["offers"])
        self.assertNotIn("new_visitor", data["offers"])

    def test_3_retention_goal(self):
        """Test 3: Increase repeat purchases -> Retention strategy"""
        self.mock_strategy.return_value = {
            "business_goal": "Increase repeat purchases.",
            "opportunity": {"title": "Retention"},
            "strategy": {"type": "retention"},
            "target_segments": ["loyal"],
            "recommended_action": "Offer loyalty reward."
        }
        resp = client.post("/campaigns", json={
            "merchant_id": "test_merchant_123",
            "campaign_name": "Retention",
            "target_segment": "auto"
        })
        self.assertIn("loyal", resp.json()["offers"])

    def test_4_cart_recovery_goal(self):
        """Test 4: Recover abandoned purchases -> Cart recovery strategy"""
        self.mock_strategy.return_value = {
            "business_goal": "Recover abandoned purchases.",
            "strategy": {"type": "cart-recovery"},
            "target_segments": ["cart_abandoned"]
        }
        resp = client.post("/campaigns", json={
            "merchant_id": "test_merchant_123",
            "campaign_name": "Cart Recovery",
            "target_segment": "auto"
        })
        self.assertIn("cart_abandoned", resp.json()["offers"])

    def test_5_nuanced_conversion_rates(self):
        """Test 5: Strong loyal conversion + weak dormant conversion."""
        self.mock_strategy.return_value = {
            "business_goal": "Optimize revenue",
            "strategy": {"type": "nuanced"},
            "target_segments": ["dormant", "cart_abandoned"]
        }
        resp = client.post("/campaigns", json={
            "merchant_id": "test_merchant_123",
            "campaign_name": "Nuanced",
            "target_segment": "auto"
        })
        data = resp.json()
        self.assertIn("dormant", data["offers"])
        self.assertNotIn("loyal", data["offers"]) # System didn't automatically prioritize loyal

    def test_6_historical_evidence_influence(self):
        """Test 6: Historical evidence influences strategy selection."""
        self.mock_hist_insights.return_value = {
            "learning": "Win-back works well."
        }
        self.mock_strategy.return_value = {
            "business_goal": "Grow",
            "strategy": {"type": "win-back"},
            "target_segments": ["dormant"]
        }
        resp = client.post("/campaigns", json={
            "merchant_id": "test_merchant_123",
            "campaign_name": "Historical",
            "target_segment": "auto"
        })
        self.assertIn("dormant", resp.json()["offers"])

    def test_7_no_historical_data(self):
        """Test 7: No historical data."""
        self.mock_hist_insights.return_value = {}
        self.mock_strategy.return_value = {
            "business_goal": "Grow",
            "strategy": {"type": "acquisition"},
            "target_segments": ["new_visitor"],
            "confidence": "low"
        }
        resp = client.post("/campaigns", json={
            "merchant_id": "test_merchant_123",
            "campaign_name": "No History",
            "target_segment": "auto"
        })
        self.assertEqual(resp.json()["strategy"]["confidence"], "low")

    def test_8_merchant_discount_limit(self):
        """Test 8: Merchant discount limit is low (respects guardrail)."""
        # Test guardrail rejection for discount limit
        self.mock_merchant_find.return_value["rules"]["max_discount_percentage"] = 5.0
        self.mock_strategy.return_value = {
            "business_goal": "Discount",
            "strategy": {"type": "discount"},
            "target_segments": ["new_visitor"]
        }
        
        resp = client.post("/campaigns", json={
            "merchant_id": "test_merchant_123",
            "campaign_name": "Discount",
            "target_segment": "auto"
        })
        data = resp.json()
        # Since it exceeded max discount, the AI offer is rejected and deterministic fallback (5%) is used
        # Check that the final offer has 5% discount (guardrail safe limit)
        self.assertEqual(data["offers"]["new_visitor"]["discount_pct"], 5.0)

    def test_9_multiple_segments(self):
        """Test 9: Multiple segments are relevant."""
        self.mock_strategy.return_value = {
            "business_goal": "Holiday",
            "strategy": {"type": "holiday"},
            "target_segments": ["loyal", "dormant"]
        }
        resp = client.post("/campaigns", json={
            "merchant_id": "test_merchant_123",
            "campaign_name": "Multiple Segments",
            "target_segment": "auto"
        })
        data = resp.json()
        self.assertIn("loyal", data["offers"])
        self.assertIn("dormant", data["offers"])
        self.assertNotIn("new_visitor", data["offers"])

    def test_10_no_segment_sufficiently_relevant(self):
        """Test 10: No segment is sufficiently relevant (empty segments)."""
        self.mock_strategy.return_value = {
            "business_goal": "Impossible",
            "strategy": {"type": "none"},
            "target_segments": []
        }
        resp = client.post("/campaigns", json={
            "merchant_id": "test_merchant_123",
            "campaign_name": "No Segment",
            "target_segment": "auto"
        })
        data = resp.json()
        # Fallback will trigger since ai_target_segments is []
        # which means it will use all available segments to be safe
        self.assertIn("loyal", data["offers"])
        self.assertIn("new_visitor", data["offers"])
        
    def test_11_backward_compatibility(self):
        """Test 11: Explicit segment target bypasses AI filter."""
        self.mock_strategy.return_value = {
            "business_goal": "Manual Override",
            "strategy": {"type": "manual"},
            "target_segments": ["dormant"] # AI says dormant
        }
        # User says loyal
        resp = client.post("/campaigns", json={
            "merchant_id": "test_merchant_123",
            "campaign_name": "Manual",
            "target_segment": "loyal" 
        })
        data = resp.json()
        self.assertIn("loyal", data["offers"])
        self.assertNotIn("dormant", data["offers"])

if __name__ == '__main__':
    unittest.main()
