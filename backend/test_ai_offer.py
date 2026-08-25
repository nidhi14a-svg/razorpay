#!/usr/bin/env python
"""Test AI offer generation via OpenRouter"""

from claude_agent import get_offer_for_segment
from guardrails import validate_offer

# Merchant rules
merchant_rules = {
    "max_discount_percentage": 20,
    "min_margin_percentage": 30
}

# Test customer data for guardrails validation
test_customer = {
    "purchase_count": 0,  # new visitor
}

print("=" * 60)
print("AI OFFER GENERATION TEST - OpenRouter Integration")
print("=" * 60)
print()

segments = ["loyal", "new_visitor", "cart_abandoned", "high_value"]

for segment in segments:
    print(f"\n📝 Generating offer for: {segment.upper()}")
    print("-" * 60)
    
    try:
        # Get AI offer
        offer = get_offer_for_segment(segment, merchant_rules)
        print(f"✓ AI Response:")
        print(f"  Offer: {offer.get('offer')}")
        print(f"  Discount: {offer.get('discount_pct')}%")
        print(f"  Reasoning: {offer.get('reasoning')}")
        print()
        
        # Validate against guardrails
        print(f"✓ Guardrails Validation:")
        is_valid = validate_offer(offer, merchant_rules, test_customer)
        if is_valid:
            print(f"  ✓ Offer approved by guardrails")
        else:
            print(f"  ❌ Offer blocked by guardrails")
            
    except Exception as e:
        print(f"❌ Error: {e}")

print()
print("=" * 60)
print("Test complete!")
print("=" * 60)
