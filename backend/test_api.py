import sys
import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_api():
    print("=" * 60)
    print("TESTING FASTAPI ENDPOINTS")
    print("=" * 60)

    # 1. Test GET /health
    print("\n--- Testing GET /health ---")
    response = client.get("/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print(f"✓ /health passed: {response.json()}")

    # 2. Test POST /auth/login (Invalid payload)
    print("\n--- Testing POST /auth/login ---")
    response = client.post("/auth/login", json={"email": "wrong@example.com", "password": "wrong"})
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    print(f"✓ /auth/login handles invalid credentials gracefully (401)")

    # 3. Test POST /offers/generate with various segments
    test_customers = {
        "loyal": {"purchase_count": 5, "days_since_last_purchase": 10},
        "new_visitor": {"purchase_count": 0, "cart_status": "browsing"},
        "cart_abandoned": {"cart_status": "abandoned", "days_since_last_purchase": 0},
        "high_value": {"lifetime_value": 15000},
        "price_sensitive": {"average_order_value": 1000},
        "dormant": {"days_since_last_purchase": 100},
        "regular": {"days_since_last_purchase": 45},
        "missing_optional": {}
    }

    print("\n--- Testing POST /offers/generate ---")
    for label, customer_data in test_customers.items():
        payload = {
            "merchant_id": "demo_merchant_001",
            "customer": customer_data
        }
        
        response = client.post("/offers/generate", json=payload)
        assert response.status_code == 200, f"Failed for {label}: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "segment" in data
        assert "offer" in data
        assert "discount_percentage" in data
        assert "reason" in data
        
        # Verify guardrail constraint directly on response
        assert data["discount_percentage"] <= 20.0
        
        print(f"✓ Generated offer for {label:<16}: Segment -> {data['segment']:<15} | Discount -> {data['discount_percentage']}%")

    # 4. Test POST /payments/create-order
    print("\n--- Testing POST /payments/create-order ---")
    
    # Needs a mock because hitting it directly would trigger real Razorpay calls if .env has keys,
    # or fail if .env has no keys. Since test_api runs in the current environment, let's mock it using patch.
    import unittest.mock as mock
    with mock.patch('razorpay_service.create_razorpay_order') as mock_create_order:
        mock_create_order.return_value = {
            "id": "order_test123",
            "amount": 50000,
            "currency": "INR",
            "status": "created"
        }
        
        response = client.post("/payments/create-order", json={
            "amount": 500.0,
            "currency": "INR",
            "receipt": "test_receipt_1"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["order_id"] == "order_test123"
        assert data["amount"] == 50000
        assert data["currency"] == "INR"
        assert data["status"] == "created"
        print(f"✓ /payments/create-order passed successfully")
        
        # Test invalid amount gracefully handled
        mock_create_order.side_effect = ValueError("Amount must be greater than 0")
        response = client.post("/payments/create-order", json={
            "amount": -50.0
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✓ /payments/create-order gracefully handles invalid amounts (400 Bad Request)")

    # 5. Test POST /payments/verify
    print("\n--- Testing POST /payments/verify ---")
    
    with mock.patch('razorpay_service.verify_payment_signature') as mock_verify:
        # Test valid signature
        mock_verify.return_value = True
        response = client.post("/payments/verify", json={
            "razorpay_order_id": "order_123",
            "razorpay_payment_id": "pay_123",
            "razorpay_signature": "sig_valid"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["status"] == "success"
        assert data["verified"] is True
        print(f"✓ /payments/verify passed for valid signature")
        
        # Test invalid signature
        mock_verify.return_value = False
        response = client.post("/payments/verify", json={
            "razorpay_order_id": "order_123",
            "razorpay_payment_id": "pay_123",
            "razorpay_signature": "sig_invalid"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✓ /payments/verify correctly rejects invalid signature (400 Bad Request)")

    # 6. Test Invalid Request Data
    print("\n--- Testing Invalid Request Data ---")
    response = client.post("/offers/generate", json={"customer": "invalid string instead of object"})
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    print(f"✓ API gracefully rejects invalid schema (422 Unprocessable Entity)")
    
    print("\n" + "=" * 60)
    print("✅ ALL API TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        test_api()
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
