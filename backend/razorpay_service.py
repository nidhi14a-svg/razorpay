import razorpay
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY"), os.getenv("RAZORPAY_SECRET"))
)

def create_coupon(discount_pct: int, campaign_id: str, max_uses: int = 100) -> dict:
    """
    Create a coupon in Razorpay.
    
    Args:
        discount_pct: 10 means 10% off
        campaign_id: unique identifier for this campaign
        max_uses: how many times can coupon be used
    
    Returns:
        Coupon details from Razorpay
    """
    
    try:
        coupon = razorpay_client.coupon.create(
            percent=discount_pct,
            max_uses=max_uses,
            description=f"Campaign: {campaign_id}",
            max_discount_amount=5000  # Max discount in INR
        )
        print(f"✓ Coupon created: {coupon['code']}")
        return coupon
    
    except Exception as e:
        print(f"❌ Error creating coupon: {e}")
        return None


def create_payment_link(amount: int, coupon_code: str = None, customer_name: str = None) -> dict:
    """
    Create a payment link in Razorpay.
    
    Args:
        amount: amount in paise (5000 paise = ₹50)
        coupon_code: coupon code to apply
        customer_name: customer's name
    
    Returns:
        Payment link with URL
    """
    
    try:
        payload = {
            "amount": amount,
            "currency": "INR",
            "description": f"Order for {customer_name}",
            "customer_notify": 1,
            "notify": {
                "sms": True,
                "email": True
            }
        }
        
        if coupon_code:
            payload["coupon_code"] = coupon_code
        
        payment_link = razorpay_client.payment_link.create(**payload)
        print(f"✓ Payment link created: {payment_link['short_url']}")
        return payment_link
    
    except Exception as e:
        print(f"❌ Error creating payment link: {e}")
        return None