import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
client = TestClient(app)

class TestPaymentVerificationLifecycle(unittest.TestCase):
    
    def setUp(self):
        # Patch collections
        self.patcher_orders = patch('main.orders_collection')
        self.mock_orders = self.patcher_orders.start()
        
        self.patcher_offers = patch('main.offers_collection')
        self.mock_offers = self.patcher_offers.start()
        
        # Patch Razorpay verify
        self.patcher_rzp_verify = patch('razorpay_service.verify_payment_signature')
        self.mock_rzp_verify = self.patcher_rzp_verify.start()

    def tearDown(self):
        self.patcher_orders.stop()
        self.patcher_offers.stop()
        self.patcher_rzp_verify.stop()

    def test_valid_signature_updates_lifecycle(self):
        """Test valid signature successfully updates order and offer"""
        self.mock_orders.find_one.return_value = {
            "razorpay_order_id": "order_123",
            "offer_id": "offer_456",
            "payment_status": "ORDER_CREATED"
        }
        self.mock_rzp_verify.return_value = True
        
        response = client.post("/payments/verify", json={
            "razorpay_order_id": "order_123",
            "razorpay_payment_id": "pay_789",
            "razorpay_signature": "valid_sig_hash"
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["verified"], True)
        
        # Verify order update
        self.mock_orders.update_one.assert_called_once()
        order_update_args = self.mock_orders.update_one.call_args[0]
        self.assertEqual(order_update_args[0], {"razorpay_order_id": "order_123"})
        self.assertEqual(order_update_args[1]["$set"]["payment_status"], "PAYMENT_VERIFIED")
        self.assertEqual(order_update_args[1]["$set"]["razorpay_payment_id"], "pay_789")
        self.assertIn("verified_at", order_update_args[1]["$set"])
        
        # Verify offer update
        self.mock_offers.update_one.assert_called_once()
        offer_update_args = self.mock_offers.update_one.call_args[0]
        self.assertEqual(offer_update_args[0], {"offer_id": "offer_456"})
        self.assertEqual(offer_update_args[1]["$set"]["status"], "PAYMENT_VERIFIED")

    def test_invalid_signature_preserves_state(self):
        """Test invalid signature rejects without DB changes"""
        self.mock_orders.find_one.return_value = {
            "razorpay_order_id": "order_123",
            "payment_status": "ORDER_CREATED"
        }
        self.mock_rzp_verify.return_value = False
        
        response = client.post("/payments/verify", json={
            "razorpay_order_id": "order_123",
            "razorpay_payment_id": "pay_789",
            "razorpay_signature": "invalid_sig_hash"
        })
        
        self.assertEqual(response.status_code, 400)
        
        # Verify no DB updates
        self.mock_orders.update_one.assert_not_called()
        self.mock_offers.update_one.assert_not_called()

    def test_order_not_found(self):
        """Test missing order throws 404"""
        self.mock_orders.find_one.return_value = None
        
        response = client.post("/payments/verify", json={
            "razorpay_order_id": "order_123",
            "razorpay_payment_id": "pay_789",
            "razorpay_signature": "any_sig"
        })
        
        self.assertEqual(response.status_code, 404)
        self.mock_rzp_verify.assert_not_called()

    def test_idempotent_repeated_verification(self):
        """Test repeated valid verification requests are idempotent"""
        self.mock_orders.find_one.return_value = {
            "razorpay_order_id": "order_123",
            "payment_status": "PAYMENT_VERIFIED",
            "razorpay_payment_id": "pay_789"
        }
        
        response = client.post("/payments/verify", json={
            "razorpay_order_id": "order_123",
            "razorpay_payment_id": "pay_789",
            "razorpay_signature": "valid_sig_hash"
        })
        
        # Succeeds immediately without re-checking signature or rewriting DB
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["verified"], True)
        self.mock_rzp_verify.assert_not_called()
        self.mock_orders.update_one.assert_not_called()
        
    def test_missing_request_fields(self):
        """Test incomplete payloads fail Pydantic validation cleanly"""
        response = client.post("/payments/verify", json={
            "razorpay_order_id": "order_123"
            # Missing payment_id and signature
        })
        self.assertEqual(response.status_code, 422)

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    unittest.main()
