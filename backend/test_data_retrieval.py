import sys
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

class TestDataRetrievalAPI(unittest.TestCase):
    
    def setUp(self):
        self.patcher_campaigns = patch('main.campaigns_collection')
        self.mock_campaigns = self.patcher_campaigns.start()
        
        self.patcher_offers = patch('main.offers_collection')
        self.mock_offers = self.patcher_offers.start()
        
        self.patcher_customers = patch('main.customers_collection')
        self.mock_customers = self.patcher_customers.start()

    def tearDown(self):
        self.patcher_campaigns.stop()
        self.patcher_offers.stop()
        self.patcher_customers.stop()

    def test_list_customers(self):
        # Mock distinct to return [c1, c2] for the merchant
        self.mock_offers.distinct.return_value = ["c1", "c2"]
        
        # Mock the cursor behavior for customers_collection.find()
        cursor_mock = self.mock_customers.find.return_value
        cursor_mock.skip.return_value = cursor_mock
        cursor_mock.limit.return_value = [
            {"id": "c1", "purchase_count": 10, "days_since_last_purchase": 5, "lifetime_value": 50000},
            {"id": "c2", "purchase_count": 0, "days_since_last_purchase": 999, "lifetime_value": 0}
        ]
        
        response = client.get("/customers?merchant_id=merch_1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["total"], 2)
        self.assertEqual(len(data["items"]), 2)
        
        # Ensure segmentation was correctly applied on the fly
        self.assertEqual(data["items"][0]["segment"], "loyal")
        self.assertEqual(data["items"][1]["segment"], "dormant")

    def test_list_customers_missing_merchant(self):
        response = client.get("/customers")
        self.assertEqual(response.status_code, 422) # Missing required query param

    def test_get_customer_detail(self):
        # Passed isolation check
        self.mock_offers.find_one.return_value = {"merchant_id": "merch_1"}
        self.mock_customers.find_one.return_value = {"id": "c1", "purchase_count": 10}
        
        response = client.get("/customers/c1?merchant_id=merch_1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], "c1")

    def test_get_customer_isolation_failure(self):
        # Failed isolation check (no interaction with this merchant)
        self.mock_offers.find_one.return_value = None
        
        response = client.get("/customers/c1?merchant_id=merch_2")
        self.assertEqual(response.status_code, 404)
        
        response = client.get("/customers/c1/segment?merchant_id=merch_2")
        self.assertEqual(response.status_code, 404)

    def test_list_offers(self):
        cursor_mock = self.mock_offers.find.return_value
        cursor_mock.skip.return_value = cursor_mock
        cursor_mock.limit.return_value = [{"offer_id": "o1"}, {"offer_id": "o2"}]
        self.mock_offers.count_documents.return_value = 100
        
        response = client.get("/offers?merchant_id=merch_1&page=2&limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["total"], 100)
        self.assertEqual(data["page"], 2)
        self.assertEqual(data["limit"], 5)
        self.assertEqual(len(data["items"]), 2)

    def test_list_campaigns(self):
        cursor_mock = self.mock_campaigns.find.return_value
        cursor_mock.skip.return_value = cursor_mock
        cursor_mock.limit.return_value = [{"campaign_id": "camp1"}]
        self.mock_campaigns.count_documents.return_value = 1
        
        response = client.get("/campaigns?merchant_id=merch_1&status=ACTIVE")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify query was correctly formulated
        self.mock_campaigns.find.assert_called_with({"merchant_id": "merch_1", "status": "ACTIVE"}, {"_id": 0})
        self.assertEqual(data["items"][0]["campaign_id"], "camp1")

    def test_get_campaign_detail(self):
        self.mock_campaigns.find_one.return_value = {"campaign_id": "camp1", "merchant_id": "merch_1"}
        self.mock_offers.count_documents.return_value = 50
        
        response = client.get("/campaigns/camp1?merchant_id=merch_1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["offers_generated"], 50)
        
    def test_get_campaign_isolation_failure(self):
        self.mock_campaigns.find_one.return_value = None # Doesn't exist for this merchant
        
        response = client.get("/campaigns/camp1?merchant_id=merch_B")
        self.assertEqual(response.status_code, 404)
        
        # Checking analytics endpoints
        response = client.get("/campaigns/camp1/analytics?merchant_id=merch_B")
        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    unittest.main()
