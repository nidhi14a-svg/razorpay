import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import uuid
from main import app

client = TestClient(app)

class TestCampaignOrchestration(unittest.TestCase):
    
    def setUp(self):
        # Patch collections
        self.patcher_merchants = patch('main.merchants_collection')
        self.mock_merchants = self.patcher_merchants.start()
        
        self.patcher_campaigns = patch('main.campaigns_collection')
        self.mock_campaigns = self.patcher_campaigns.start()
        
        self.patcher_customers = patch('main.customers_collection')
        self.mock_customers = self.patcher_customers.start()
        
        self.patcher_offers = patch('main.offers_collection')
        self.mock_offers = self.patcher_offers.start()
        
        # Patch AI logic
        self.patcher_ai = patch('claude_agent.get_offer_for_segment')
        self.mock_ai = self.patcher_ai.start()
        
        self.patcher_strategy = patch('claude_agent.determine_campaign_strategy')
        self.mock_strategy = self.patcher_strategy.start()
        self.mock_strategy.return_value = {
            "business_goal": "Test",
            "strategy": {"type": "test"},
            "target_segments": ["loyal"]
        }

        self.patcher_hist_insights = patch('historical_analyzer.get_historical_learning_insights')
        self.mock_hist_insights = self.patcher_hist_insights.start()
        self.mock_hist_insights.return_value = {}

        self.patcher_intelligence = patch('merchant_intelligence.get_merchant_campaign_intelligence')
        self.mock_intelligence = self.patcher_intelligence.start()
        self.mock_intelligence.return_value = {}

    def tearDown(self):
        self.patcher_merchants.stop()
        self.patcher_campaigns.stop()
        self.patcher_customers.stop()
        self.patcher_offers.stop()
        self.patcher_ai.stop()
        self.patcher_strategy.stop()
        self.patcher_hist_insights.stop()
        self.patcher_intelligence.stop()

    def test_merchant_not_found(self):
        """Test missing merchant throws 404"""
        self.mock_merchants.find_one.return_value = None
        response = client.post("/campaigns", json={
            "merchant_id": "invalid",
            "campaign_name": "Test",
            "target_segment": "loyal"
        })
        self.assertEqual(response.status_code, 404)
        
    def test_idempotent_campaign(self):
        """Test exactly identical duplicate campaigns don't create twice"""
        self.mock_merchants.find_one.return_value = {"merchant_id": "merch_1"}
        self.mock_campaigns.find_one.return_value = {
            "campaign_id": "camp_123",
            "merchant_id": "merch_1",
            "campaign_name": "Test",
            "target_segment": "loyal",
            "status": "ACTIVE",
            "created_at": "timestamp"
        }
        self.mock_offers.count_documents.return_value = 5
        
        response = client.post("/campaigns", json={
            "merchant_id": "merch_1",
            "campaign_name": "Test",
            "target_segment": "loyal"
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["offers_generated"], 5)
        self.assertEqual(response.json()["campaign_id"], "camp_123")
        
        # Ensure insert wasn't called
        self.mock_campaigns.insert_one.assert_not_called()

    def test_successful_campaign_creation(self):
        """Test successful campaign generation targeted at loyal segment"""
        # Mock merchant
        self.mock_merchants.find_one.return_value = {
            "merchant_id": "merch_1",
            "rules": {"max_discount_percentage": 50, "min_margin_percentage": 10}
        }
        
        # No existing campaign
        self.mock_campaigns.find_one.return_value = None
        
        # Mock 3 customers (2 loyal, 1 dormant)
        self.mock_customers.find.return_value = [
            {"id": "c1", "purchase_count": 5, "days_since_last_purchase": 5, "lifetime_value": 20000}, # loyal
            {"id": "c2", "purchase_count": 0, "days_since_last_purchase": 999, "lifetime_value": 0, "cart_status": "abandoned"}, # cart abandoned
            {"id": "c3", "purchase_count": 10, "days_since_last_purchase": 2, "lifetime_value": 50000}, # loyal
        ]
        
        # Mock AI to generate valid offers (0% for loyal)
        self.mock_ai.return_value = {"reason": "0% off", "recommended_offer_type": "percentage_discount", "confidence": 1.0, "recommended_discount_percentage": 0}
        
        response = client.post("/campaigns", json={
            "merchant_id": "merch_1",
            "campaign_name": "Loyalty Drive",
            "target_segment": "loyal"
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["status"], "ACTIVE")
        self.assertEqual(data["offers_generated"], 2) # Only 2 loyal customers
        self.assertEqual(data["target_segment"], "loyal")
        
        # Verify db insert was called for campaign and offers
        self.mock_campaigns.insert_one.assert_called_once()
        self.assertEqual(self.mock_offers.insert_one.call_count, 2)
        
        # Verify campaign final status was updated
        self.mock_campaigns.update_one.assert_called_once()
        update_args = self.mock_campaigns.update_one.call_args[0]
        self.assertEqual(update_args[1]["$set"]["status"], "ACTIVE")

    def test_campaign_generation_failure(self):
        """Test campaign where no valid offers could be generated defaults to FAILED status"""
        self.mock_merchants.find_one.return_value = {"merchant_id": "merch_1"}
        self.mock_campaigns.find_one.return_value = None
        
        # 1 customer matching criteria
        self.mock_customers.find.return_value = [
            {"id": "c1", "purchase_count": 5, "days_since_last_purchase": 5, "lifetime_value": 20000} # loyal
        ]
        
        # AI totally fails
        self.mock_ai.side_effect = Exception("AI Offline")
        
        response = client.post("/campaigns", json={
            "merchant_id": "merch_1",
            "campaign_name": "Loyalty Drive",
            "target_segment": "loyal"
        })
        
        self.assertEqual(response.status_code, 200) # Still 200, the orchestration didn't break
        self.assertEqual(response.json()["offers_generated"], 0)
        self.assertEqual(response.json()["status"], "FAILED") # But campaign failed

    def test_get_campaign(self):
        """Test campaign retrieval endpoint"""
        self.mock_campaigns.find_one.return_value = {
            "campaign_id": "camp_123",
            "campaign_name": "Test"
        }
        self.mock_offers.count_documents.return_value = 10
        
        response = client.get("/campaigns/camp_123?merchant_id=merch_1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["offers_generated"], 10)

    def test_get_campaign_offers(self):
        """Test offers retrieval endpoint"""
        self.mock_campaigns.find_one.return_value = {"campaign_id": "camp_123"}
        self.mock_offers.find.return_value.skip.return_value.limit.return_value = [
            {"offer_id": "o1", "discount_percentage": 10.0},
            {"offer_id": "o2", "discount_percentage": 5.0}
        ]
        
        response = client.get("/campaigns/camp_123/offers?merchant_id=merch_1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["items"]), 2)

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    unittest.main()
