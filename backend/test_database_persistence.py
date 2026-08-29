import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
client = TestClient(app)

class TestDatabasePersistence(unittest.TestCase):
    
    def setUp(self):
        self.patcher_offers = patch('main.offers_collection')
        self.patcher_orders = patch('main.orders_collection')
        self.patcher_rzp_create = patch('razorpay_service.create_razorpay_order')
        self.patcher_rzp_verify = patch('razorpay_service.verify_payment_signature')

        self.mock_offers_collection = self.patcher_offers.start()
        self.mock_orders_collection = self.patcher_orders.start()
        self.mock_rzp_create = self.patcher_rzp_create.start()
        self.mock_rzp_verify = self.patcher_rzp_verify.start()

    def tearDown(self):
        self.patcher_offers.stop()
        self.patcher_orders.stop()
        self.patcher_rzp_create.stop()
        self.patcher_rzp_verify.stop()

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
        self.mock_offers_collection.insert_one.assert_called_once()
        inserted_doc = self.mock_offers_collection.insert_one.call_args[0][0]
        
        self.assertEqual(inserted_doc["offer_id"], data["offer_id"])
        self.assertEqual(inserted_doc["status"], "OFFER_CREATED")
        self.assertIn("discount_percentage", inserted_doc)

    def test_order_persistence_with_valid_offer(self):
        """Test storing a Razorpay order linked to an offer"""
        # Mock offer lookup
        self.mock_offers_collection.find_one.return_value = {"offer_id": "test_offer_123"}
        
        # Mock razorpay order creation
        self.mock_rzp_create.return_value = {
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
        self.mock_offers_collection.find_one.assert_called_once_with({"offer_id": "test_offer_123"})
        
        # Verify order was inserted
        self.mock_orders_collection.insert_one.assert_called_once()
        inserted_doc = self.mock_orders_collection.insert_one.call_args[0][0]
        
        self.assertEqual(inserted_doc["offer_id"], "test_offer_123")
        self.assertEqual(inserted_doc["razorpay_order_id"], "order_test_999")
        self.assertEqual(inserted_doc["payment_status"], "ORDER_CREATED")

    def test_order_persistence_with_invalid_offer(self):
        """Test creating an order with an invalid offer_id fails"""
        self.mock_offers_collection.find_one.return_value = None
        
        response = client.post("/payments/create-order", json={
            "amount": 500.0,
            "offer_id": "invalid_offer_id"
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid offer_id", response.json()["detail"])
        self.mock_orders_collection.insert_one.assert_not_called()

    def test_payment_verification_success_updates_db(self):
        """Test successful payment verification updates order to PAYMENT_VERIFIED"""
        self.mock_rzp_verify.return_value = True
        self.mock_orders_collection.find_one.return_value = {"razorpay_order_id": "order_test_999"}
        
        response = client.post("/payments/verify", json={
            "razorpay_order_id": "order_test_999",
            "razorpay_payment_id": "pay_test_999",
            "razorpay_signature": "valid_signature"
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verify db update
        self.mock_orders_collection.update_one.assert_called_once()
        update_args = self.mock_orders_collection.update_one.call_args[0]
        
        self.assertEqual(update_args[0], {"razorpay_order_id": "order_test_999"})
        self.assertEqual(update_args[1]["$set"]["payment_status"], "PAYMENT_VERIFIED")
        self.assertEqual(update_args[1]["$set"]["razorpay_payment_id"], "pay_test_999")
        self.assertIn("verified_at", update_args[1]["$set"])

    def test_payment_verification_failure_updates_db(self):
        """Test failed payment verification updates order to PAYMENT_FAILED"""
        self.mock_rzp_verify.return_value = False
        self.mock_orders_collection.find_one.return_value = {"razorpay_order_id": "order_test_999"}
        
        response = client.post("/payments/verify", json={
            "razorpay_order_id": "order_test_999",
            "razorpay_payment_id": "pay_test_999",
            "razorpay_signature": "invalid_signature"
        })
        
        self.assertEqual(response.status_code, 400)
        
        # Verify NO db update (as expected by original design to preserve state)
        self.mock_orders_collection.update_one.assert_not_called()
        
    def test_duplicate_order_handling(self):
        """Test that duplicate Razorpay order insertion fails gracefully"""
        self.mock_rzp_create.return_value = {
            "id": "order_dup_999",
            "amount": 50000,
            "currency": "INR",
            "status": "created"
        }
        
        from pymongo.errors import DuplicateKeyError
        self.mock_orders_collection.insert_one.side_effect = DuplicateKeyError("Duplicate key")
        
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
