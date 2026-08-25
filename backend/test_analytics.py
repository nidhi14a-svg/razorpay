import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

class TestCampaignAnalytics(unittest.TestCase):
    
    def setUp(self):
        # Patch collections
        self.patcher_campaigns = patch('analytics.campaigns_collection')
        self.mock_campaigns = self.patcher_campaigns.start()
        
        self.patcher_offers = patch('analytics.offers_collection')
        self.mock_offers = self.patcher_offers.start()

    def tearDown(self):
        self.patcher_campaigns.stop()
        self.patcher_offers.stop()

    def test_campaign_not_found(self):
        self.mock_campaigns.find_one.return_value = None
        
        response = client.get("/campaigns/missing_camp/analytics")
        self.assertEqual(response.status_code, 404)
        
        response2 = client.get("/campaigns/missing_camp/analytics/segments")
        self.assertEqual(response2.status_code, 404)

    def test_campaign_with_no_offers(self):
        self.mock_campaigns.find_one.return_value = {"campaign_id": "c1"}
        self.mock_offers.aggregate.return_value = [] # DB returns empty aggregation
        
        response = client.get("/campaigns/c1/analytics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Zero division case safely handled
        self.assertEqual(data["total_customers"], 0)
        self.assertEqual(data["total_offers"], 0)
        self.assertEqual(data["total_orders"], 0)
        self.assertEqual(data["conversion_rate"], 0.0)
        self.assertEqual(data["average_order_value"], 0.0)
        self.assertEqual(data["revenue"], 0.0)

    def test_campaign_with_offers_but_no_payments(self):
        self.mock_campaigns.find_one.return_value = {"campaign_id": "c1"}
        
        # 2 customers, 2 offers, no orders
        self.mock_offers.aggregate.return_value = [{
            "_id": None,
            "customers_set": ["cust_1", "cust_2"],
            "offers_set": ["off_1", "off_2"],
            "total_orders": 0,
            "verified_payments": 0,
            "failed_payments": 0,
            "total_revenue_paise": 0
        }]
        
        response = client.get("/campaigns/c1/analytics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["total_customers"], 2)
        self.assertEqual(data["total_offers"], 2)
        self.assertEqual(data["conversion_rate"], 0.0) # Zero verified, so 0%

    def test_revenue_and_conversion_calculation(self):
        self.mock_campaigns.find_one.return_value = {"campaign_id": "c1"}
        
        # 10 offers, 5 orders, 4 verified, 1 failed, 2000 INR revenue (200000 paise)
        self.mock_offers.aggregate.return_value = [{
            "_id": None,
            "customers_set": ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10"],
            "offers_set": ["o1", "o2", "o3", "o4", "o5", "o6", "o7", "o8", "o9", "o10"],
            "total_orders": 5,
            "verified_payments": 4,
            "failed_payments": 1,
            "total_revenue_paise": 200000 # 2000 INR
        }]
        
        response = client.get("/campaigns/c1/analytics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["total_offers"], 10)
        self.assertEqual(data["verified_payments"], 4)
        self.assertEqual(data["failed_payments"], 1)
        self.assertEqual(data["revenue"], 2000.00)
        self.assertEqual(data["conversion_rate"], 40.0) # 4 / 10 * 100
        self.assertEqual(data["average_order_value"], 500.0) # 2000 / 4

    def test_segment_breakdown_analytics(self):
        self.mock_campaigns.find_one.return_value = {"campaign_id": "c1"}
        
        # Mock aggregation returning grouped data
        self.mock_offers.aggregate.return_value = [
            {
                "_id": "loyal",
                "customers_set": ["c1"],
                "offers_set": ["o1"],
                "total_orders": 1,
                "verified_payments": 1,
                "failed_payments": 0,
                "total_revenue_paise": 50000 # 500 INR
            },
            {
                "_id": "new_visitor",
                "customers_set": ["c2", "c3"],
                "offers_set": ["o2", "o3"],
                "total_orders": 0,
                "verified_payments": 0,
                "failed_payments": 0,
                "total_revenue_paise": 0
            }
        ]
        
        response = client.get("/campaigns/c1/analytics/segments")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(len(data), 2)
        
        # Validate loyal
        loyal = next(s for s in data if s["segment"] == "loyal")
        self.assertEqual(loyal["total_customers"], 1)
        self.assertEqual(loyal["conversion_rate"], 100.0)
        self.assertEqual(loyal["revenue"], 500.0)
        
        # Validate new_visitor
        new = next(s for s in data if s["segment"] == "new_visitor")
        self.assertEqual(new["total_customers"], 2)
        self.assertEqual(new["conversion_rate"], 0.0)
        self.assertEqual(new["revenue"], 0.0)

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    unittest.main()
