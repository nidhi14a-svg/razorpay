import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
client = TestClient(app)

class TestOfferPaymentOrder(unittest.TestCase):
    
    def setUp(self):
        # Patch offers_collection and orders_collection
        self.patcher_offers = patch('main.offers_collection')
        self.mock_offers_collection = self.patcher_offers.start()
        
        self.patcher_orders = patch('main.orders_collection')
        self.mock_orders_collection = self.patcher_orders.start()
        
        # Patch razorpay service
        self.patcher_rzp = patch('razorpay_service.create_razorpay_order')
        self.mock_rzp = self.patcher_rzp.start()

    def tearDown(self):
        self.patcher_offers.stop()
        self.patcher_orders.stop()
        self.patcher_rzp.stop()

    def test_valid_offer_creates_order(self):
        """Test a valid offer calculates the amount and creates an order"""
        # Mock offer lookup
        self.mock_offers_collection.find_one.return_value = {
            "offer_id": "offer_123",
            "discount_percentage": 10.0,
            "status": "OFFER_CREATED",
            "merchant_id": "test_merchant",
            "customer_id": "cust_123"
        }
        
        # Mock no existing order
        self.mock_orders_collection.find_one.return_value = None
        
        # Mock razorpay order creation
        self.mock_rzp.return_value = {
            "id": "order_rzp_999",
            "amount": 9000, # 100 INR - 10% = 90 INR = 9000 paise
            "currency": "INR",
            "status": "created"
        }
        
        response = client.post("/offers/offer_123/create-payment-order", json={
            "original_amount": 100.0,
            "currency": "INR"
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["order_id"], "order_rzp_999")
        self.assertEqual(data["amount"], 9000)
        self.assertEqual(data["status"], "ORDER_CREATED")
        
        # Verify db insert was called
        self.mock_orders_collection.insert_one.assert_called_once()
        inserted_doc = self.mock_orders_collection.insert_one.call_args[0][0]
        self.assertEqual(inserted_doc["offer_id"], "offer_123")
        self.assertEqual(inserted_doc["razorpay_order_id"], "order_rzp_999")
        
        # Verify offer status was updated
        self.mock_offers_collection.update_one.assert_called_once_with(
            {"offer_id": "offer_123"},
            {"$set": {"status": "ORDER_CREATED"}}
        )
        
        # Verify razorpay create was called with CORRECT amount
        self.mock_rzp.assert_called_once_with(
            amount_inr=90.0,
            currency="INR",
            receipt=None,
            notes=None
        )

    def test_offer_not_found(self):
        """Test missing offer returns 404"""
        self.mock_offers_collection.find_one.return_value = None
        
        response = client.post("/offers/invalid_offer/create-payment-order", json={
            "original_amount": 100.0
        })
        
        self.assertEqual(response.status_code, 404)
        self.mock_rzp.assert_not_called()

    def test_invalid_already_paid_offer(self):
        """Test already paid offer is rejected"""
        self.mock_offers_collection.find_one.return_value = {
            "offer_id": "offer_123",
            "status": "PAYMENT_VERIFIED"
        }
        
        response = client.post("/offers/offer_123/create-payment-order", json={
            "original_amount": 100.0
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("no longer eligible", response.json()["detail"])
        self.mock_rzp.assert_not_called()

    def test_reuse_existing_pending_order(self):
        """Test idempotency: reuse existing pending order if amounts match"""
        self.mock_offers_collection.find_one.return_value = {
            "offer_id": "offer_123",
            "discount_percentage": 20.0, # 20% discount on 100 = 80 = 8000 paise
            "status": "ORDER_CREATED"
        }
        
        # Mock existing order matching the amount
        self.mock_orders_collection.find_one.return_value = {
            "offer_id": "offer_123",
            "razorpay_order_id": "order_existing_123",
            "amount": 8000,
            "currency": "INR",
            "payment_status": "ORDER_CREATED"
        }
        
        response = client.post("/offers/offer_123/create-payment-order", json={
            "original_amount": 100.0
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["order_id"], "order_existing_123")
        
        # Verify Razorpay was NOT called again
        self.mock_rzp.assert_not_called()
        self.mock_orders_collection.insert_one.assert_not_called()

    def test_razorpay_failure(self):
        """Test Razorpay service failure returns 502"""
        self.mock_offers_collection.find_one.return_value = {
            "offer_id": "offer_123",
            "discount_percentage": 10.0,
            "status": "OFFER_CREATED"
        }
        self.mock_orders_collection.find_one.return_value = None
        
        # Razorpay fails (returns empty/None)
        self.mock_rzp.return_value = None
        
        response = client.post("/offers/offer_123/create-payment-order", json={
            "original_amount": 100.0
        })
        
        self.assertEqual(response.status_code, 502)
        self.assertIn("Failed to create Razorpay order", response.json()["detail"])
        self.mock_orders_collection.insert_one.assert_not_called()

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    unittest.main()
