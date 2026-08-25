import sys
import unittest
from unittest.mock import patch, MagicMock

import razorpay_service
from razorpay_service import create_coupon, create_payment_link, create_offer_payment_link

class TestRazorpayService(unittest.TestCase):
    
    @patch('razorpay_service.get_razorpay_client')
    def test_create_coupon_valid(self, mock_get_client):
        # Mock client
        mock_client = MagicMock()
        mock_client.coupon.create.return_value = {
            "id": "coupon_123",
            "code": "SAVE10",
            "percent": 10
        }
        mock_get_client.return_value = mock_client
        
        result = create_coupon(10, "camp_1")
        
        self.assertEqual(result["id"], "coupon_123")
        self.assertEqual(result["code"], "SAVE10")
        mock_client.coupon.create.assert_called_once_with(
            percent=10, max_uses=100, description="Campaign: camp_1", max_discount_amount=5000
        )
        
    def test_create_coupon_invalid_negative(self):
        with self.assertRaises(ValueError):
            create_coupon(-5, "camp_1")
            
    @patch('razorpay_service.get_razorpay_client')
    def test_create_payment_link_valid(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.payment_link.create.return_value = {
            "id": "plink_123",
            "short_url": "https://rzp.io/i/link123"
        }
        mock_get_client.return_value = mock_client
        
        result = create_payment_link(450000, "SAVE10", "Alice", "alice@example.com")
        
        self.assertEqual(result["short_url"], "https://rzp.io/i/link123")
        mock_client.payment_link.create.assert_called_once()
        call_args = mock_client.payment_link.create.call_args[0][0]
        self.assertEqual(call_args["amount"], 450000)
        self.assertEqual(call_args["notes"]["coupon_code"], "SAVE10")
        
    def test_create_payment_link_invalid_amount(self):
        with self.assertRaises(ValueError):
            create_payment_link(0, "SAVE10", "Alice")
        with self.assertRaises(ValueError):
            create_payment_link(-100, "SAVE10", "Alice")
            
    @patch('razorpay_service.create_payment_link')
    @patch('razorpay_service.create_coupon')
    def test_create_offer_payment_link_with_discount(self, mock_create_coupon, mock_create_payment_link):
        mock_create_coupon.return_value = {"id": "coupon_999", "code": "SAVE20"}
        mock_create_payment_link.return_value = {"id": "plink_999", "short_url": "https://rzp.io/i/link999"}
        
        offer = {"discount_percentage": 20.0}
        customer = {"name": "Bob", "email": "bob@test.com", "id": "cust_1"}
        
        result = create_offer_payment_link(offer, "camp_2", customer)
        
        self.assertEqual(result["customer_name"], "Bob")
        self.assertEqual(result["discount"], 20.0)
        self.assertEqual(result["coupon_code"], "SAVE20")
        self.assertEqual(result["payment_link"], "https://rzp.io/i/link999")
        
        mock_create_coupon.assert_called_once_with(discount_pct=20, campaign_id="camp_2")
        # 5000 * 0.8 = 4000 INR = 400000 paise
        mock_create_payment_link.assert_called_once_with(
            amount=400000, coupon_code="SAVE20", customer_name="Bob", customer_email="bob@test.com"
        )
        
    @patch('razorpay_service.create_payment_link')
    @patch('razorpay_service.create_coupon')
    def test_create_offer_payment_link_zero_discount(self, mock_create_coupon, mock_create_payment_link):
        mock_create_payment_link.return_value = {"id": "plink_888", "short_url": "https://rzp.io/i/link888"}
        
        offer = {"discount_percentage": 0}
        customer = {"name": "Charlie"}
        
        result = create_offer_payment_link(offer, "camp_3", customer)
        
        self.assertEqual(result["discount"], 0)
        self.assertIsNone(result["coupon_code"])
        
        mock_create_coupon.assert_not_called()
        # 5000 INR = 500000 paise
        mock_create_payment_link.assert_called_once_with(
            amount=500000, coupon_code=None, customer_name="Charlie", customer_email="customer@example.com"
        )

    @patch('razorpay_service.get_razorpay_client')
    def test_create_razorpay_order_valid(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.order.create.return_value = {
            "id": "order_123",
            "amount": 50000,
            "currency": "INR",
            "status": "created"
        }
        mock_get_client.return_value = mock_client
        
        from razorpay_service import create_razorpay_order
        result = create_razorpay_order(500.0, "INR", "receipt_1", {"key": "val"})
        
        self.assertEqual(result["id"], "order_123")
        mock_client.order.create.assert_called_once_with({
            "amount": 50000,
            "currency": "INR",
            "receipt": "receipt_1",
            "notes": {"key": "val"}
        })

    def test_create_razorpay_order_invalid_amount(self):
        from razorpay_service import create_razorpay_order
        with self.assertRaises(ValueError):
            create_razorpay_order(-100.0)
        with self.assertRaises(ValueError):
            create_razorpay_order(0)

    @patch('razorpay_service.get_razorpay_client')
    def test_verify_payment_signature_valid(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.utility.verify_payment_signature.return_value = None
        mock_get_client.return_value = mock_client
        
        from razorpay_service import verify_payment_signature
        result = verify_payment_signature("order_123", "pay_123", "sig_123")
        
        self.assertTrue(result)
        mock_client.utility.verify_payment_signature.assert_called_once_with({
            'razorpay_order_id': 'order_123',
            'razorpay_payment_id': 'pay_123',
            'razorpay_signature': 'sig_123'
        })
        
    @patch('razorpay_service.get_razorpay_client')
    def test_verify_payment_signature_invalid(self, mock_get_client):
        mock_client = MagicMock()
        import razorpay
        mock_client.utility.verify_payment_signature.side_effect = razorpay.errors.SignatureVerificationError("Invalid signature")
        mock_get_client.return_value = mock_client
        
        from razorpay_service import verify_payment_signature
        result = verify_payment_signature("order_123", "pay_123", "sig_invalid")
        
        self.assertFalse(result)

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    unittest.main()
