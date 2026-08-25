import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Mock the database collections before importing main
patcher_offers = patch('database.offers_collection')
patcher_orders = patch('database.orders_collection')

mock_offers_collection = patcher_offers.start()
mock_orders_collection = patcher_orders.start()

# Also mock the razorpay service to avoid real calls
patcher_rzp_create = patch('razorpay_service.create_razorpay_order')
patcher_rzp_verify = patch('razorpay_service.verify_payment_signature')
mock_rzp_create = patcher_rzp_create.start()
mock_rzp_verify = patcher_rzp_verify.start()

from main import app
client = TestClient(app)

class TestDatabasePersistence(unittest.TestCase):
    
    @classmethod
    def tearDownClass(cls):
        patcher_offers.stop()
        patcher_orders.stop()
        patcher_rzp_create.stop()
        patcher_rzp_verify.stop()

    def setUp(self):
        # Reset mocks before each test
        mock_offers_collection.reset_mock()
        mock_orders_collection.reset_mock()
        mock_rzp_create.reset_mock()
        mock_rzp_verify.reset_mock()

    def test_offer_persistence(self):
        """Test that an offer is stored in the database when generated"""
        response = client.post("/offers/generate", json={
            "merchant_id": "demo_merchant_001",
            "customer": {"purchase_count": 5, "days_since_last_purchase": 10}
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("offer_id", data)
        
        # Verify db insert was called
        mock_offers_collection.insert_one.assert_called_once()
        inserted_doc = mock_offers_collection.insert_one.call_args[0][0]
        
        self.assertEqual(inserted_doc["offer_id"], data["offer_id"])
        self.assertEqual(inserted_doc["status"], "OFFER_CREATED")
        self.assertIn("discount_percentage", inserted_doc)

    def test_order_persistence_with_valid_offer(self):
        """Test storing a Razorpay order linked to an offer"""
        # Mock offer lookup
        mock_offers_collection.find_one.return_value = {"offer_id": "test_offer_123"}
        
        # Mock razorpay order creation
        mock_rzp_create.return_value = {
            "id": "order_test_999",
            "amount": 50000,
            "currency": "INR",
            "status": "created"
        }
        
        response = client.post("/payments/create-order", json={
            "amount": 500.0,
            "offer_id": "test_offer_123"
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verify offer was looked up
        mock_offers_collection.find_one.assert_called_once_with({"offer_id": "test_offer_123"})
        
        # Verify order was inserted
        mock_orders_collection.insert_one.assert_called_once()
        inserted_doc = mock_orders_collection.insert_one.call_args[0][0]
        
        self.assertEqual(inserted_doc["offer_id"], "test_offer_123")
        self.assertEqual(inserted_doc["razorpay_order_id"], "order_test_999")
        self.assertEqual(inserted_doc["payment_status"], "ORDER_CREATED")

    def test_order_persistence_with_invalid_offer(self):
        """Test creating an order with an invalid offer_id fails"""
        mock_offers_collection.find_one.return_value = None
        
        response = client.post("/payments/create-order", json={
            "amount": 500.0,
            "offer_id": "invalid_offer_id"
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid offer_id", response.json()["detail"])
        mock_orders_collection.insert_one.assert_not_called()

    def test_payment_verification_success_updates_db(self):
        """Test successful payment verification updates order to PAYMENT_VERIFIED"""
        mock_rzp_verify.return_value = True
        mock_orders_collection.find_one.return_value = {"razorpay_order_id": "order_test_999"}
        
        response = client.post("/payments/verify", json={
            "razorpay_order_id": "order_test_999",
            "razorpay_payment_id": "pay_test_999",
            "razorpay_signature": "valid_signature"
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verify db update
        mock_orders_collection.update_one.assert_called_once()
        update_args = mock_orders_collection.update_one.call_args[0]
        
        self.assertEqual(update_args[0], {"razorpay_order_id": "order_test_999"})
        self.assertEqual(update_args[1]["$set"]["payment_status"], "PAYMENT_VERIFIED")
        self.assertEqual(update_args[1]["$set"]["razorpay_payment_id"], "pay_test_999")
        self.assertIn("verified_at", update_args[1]["$set"])

    def test_payment_verification_failure_updates_db(self):
        """Test failed payment verification updates order to PAYMENT_FAILED"""
        mock_rzp_verify.return_value = False
        mock_orders_collection.find_one.return_value = {"razorpay_order_id": "order_test_999"}
        
        response = client.post("/payments/verify", json={
            "razorpay_order_id": "order_test_999",
            "razorpay_payment_id": "pay_test_999",
            "razorpay_signature": "invalid_signature"
        })
        
        self.assertEqual(response.status_code, 400)
        
        # Verify db update
        mock_orders_collection.update_one.assert_called_once()
        update_args = mock_orders_collection.update_one.call_args[0]
        
        self.assertEqual(update_args[0], {"razorpay_order_id": "order_test_999"})
        self.assertEqual(update_args[1]["$set"]["payment_status"], "PAYMENT_FAILED")
        self.assertNotIn("razorpay_payment_id", update_args[1]["$set"])
        
    def test_duplicate_order_handling(self):
        """Test that duplicate Razorpay order insertion fails gracefully"""
        mock_rzp_create.return_value = {
            "id": "order_dup_999",
            "amount": 50000,
            "currency": "INR",
            "status": "created"
        }
        
        from pymongo.errors import DuplicateKeyError
        mock_orders_collection.insert_one.side_effect = DuplicateKeyError("Duplicate key")
        
        # Even if DB insertion throws duplicate, the endpoint handles it gracefully
        response = client.post("/payments/create-order", json={
            "amount": 500.0
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["order_id"], "order_dup_999")

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    unittest.main()
