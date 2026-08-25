import sys
from offer_service import generate_personalized_offer

def test_pipeline():
    print("=" * 60)
    print("TESTING UNIFIED PIPELINE (Customer -> Segment -> Offer)")
    print("=" * 60)

    merchant_rules = {
        "max_discount_percentage": 20.0,
        "min_margin_percentage": 30.0
    }

    test_cases = [
        {"segment_expected": "loyal", "data": {"purchase_count": 5, "days_since_last_purchase": 10}},
        {"segment_expected": "new_visitor", "data": {"purchase_count": 0, "cart_status": "browsing"}},
        {"segment_expected": "cart_abandoned", "data": {"cart_status": "abandoned", "days_since_last_purchase": 0}},
        {"segment_expected": "high_value", "data": {"lifetime_value": 15000}},
        {"segment_expected": "price_sensitive", "data": {"average_order_value": 1000}},
        {"segment_expected": "dormant", "data": {"days_since_last_purchase": 100}},
        {"segment_expected": "regular", "data": {"days_since_last_purchase": 45}},
        # Edge case: Missing customer fields / incomplete data
        {"segment_expected": "dormant", "data": {}}
    ]

    all_passed = True

    for test in test_cases:
        expected_segment = test["segment_expected"]
        customer = test["data"]
        
        try:
            result = generate_personalized_offer(customer, merchant_rules)
            
            # Assertions
            assert result["segment"] == expected_segment, f"Expected {expected_segment}, got {result['segment']}"
            assert "offer" in result and result["offer"], "Offer missing or empty"
            assert "discount_percentage" in result, "discount_percentage missing"
            assert "reason" in result and result["reason"], "reason missing or empty"
            
            discount = result["discount_percentage"]
            max_discount = merchant_rules["max_discount_percentage"]
            assert discount <= max_discount, f"Discount {discount} exceeds max {max_discount}"
            assert "customer" in result, "customer object missing in result"
            
            print(f"✓ Passed test for segment: {expected_segment}")
            
        except Exception as e:
            print(f"❌ Failed test for segment: {expected_segment}")
            print(f"  Error: {e}")
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("✅ ALL PIPELINE TESTS PASSED!")
    else:
        print("❌ SOME PIPELINE TESTS FAILED!")
    print("=" * 60)

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    test_pipeline()
