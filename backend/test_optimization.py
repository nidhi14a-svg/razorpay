import sys
from optimization import generate_deterministic_offer
from guardrails import validate_offer

def run_tests():
    print("=" * 60)
    print("TESTING DETERMINISTIC OFFERS + GUARDRAILS")
    print("=" * 60)

    merchant_rules = {
        "max_discount_percentage": 20.0,
        "min_margin_percentage": 30.0
    }

    test_customers = {
        "loyal": {"purchase_count": 5, "days_since_last_purchase": 10},
        "new_visitor": {"purchase_count": 0, "cart_status": "browsing"},
        "cart_abandoned": {"cart_status": "abandoned", "days_since_last_purchase": 0},
        "high_value": {"lifetime_value": 15000},
        "price_sensitive": {"average_order_value": 1000},
        "dormant": {"days_since_last_purchase": 100},
        "regular": {"days_since_last_purchase": 45}
    }

    all_passed = True

    for label, cust_data in test_customers.items():
        print(f"\n--- Testing Segment Flow: {label.upper()} ---")
        
        # 1. Generate Offer
        result = generate_deterministic_offer(cust_data, merchant_rules)
        
        offer_dict = {
            "offer": result["offer"],
            "discount_pct": result["discount_percentage"]
        }
        
        print(f"Segment Identified: {result['segment']}")
        print(f"Offer Generated:    {result['offer']}")
        print(f"Discount:           {result['discount_percentage']}%")
        
        # 2. Validate against Guardrails
        print("Guardrail Check:")
        is_valid = validate_offer(offer_dict, merchant_rules, cust_data)
        
        if not is_valid:
            print(f"❌ TEST FAILED: Offer for {label} was rejected by guardrails!")
            all_passed = False
        else:
            print(f"✓ TEST PASSED: Offer approved.")

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED SUCCESSFULLY! ✅")
    else:
        print("SOME TESTS FAILED! ❌")
    print("=" * 60)

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    run_tests()
