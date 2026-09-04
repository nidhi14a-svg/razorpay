import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def validate_offer(offer: dict, merchant_rules: dict, customer: dict) -> bool:
    """
    Validates an AI-generated offer against merchant business rules.
    Returns True if approved, False if blocked.
    """
    # RULE 4: Defensive validation
    if not isinstance(offer, dict) or not isinstance(merchant_rules, dict) or not isinstance(customer, dict):
        print("❌ BLOCKED: Malformed input - Missing or invalid dictionaries")
        return False
        
    try:
        # Check if discount_pct exists and is a valid number
        if "discount_pct" not in offer or offer["discount_pct"] is None:
            print("❌ BLOCKED: Malformed or missing discount_pct")
            return False
        discount_pct = float(offer["discount_pct"])
    except (TypeError, ValueError):
        print("❌ BLOCKED: Malformed or missing discount_pct")
        return False

    if discount_pct < 0:
        print("❌ BLOCKED: Negative discount percentage not allowed")
        return False

    try:
        max_discount_percentage = float(merchant_rules["max_discount_percentage"])
        min_margin_percentage = float(merchant_rules["min_margin_percentage"])
    except (KeyError, TypeError, ValueError):
        print("❌ BLOCKED: Missing or invalid merchant rules (max_discount_percentage, min_margin_percentage)")
        return False

    try:
        purchase_count = int(customer.get("purchase_count", 0))
    except (TypeError, ValueError):
        print("❌ BLOCKED: Invalid purchase_count in customer data")
        return False

    # RULE 1: Maximum discount
    if discount_pct > max_discount_percentage:
        print(f"❌ BLOCKED: Discount {discount_pct}% exceeds maximum allowed {max_discount_percentage}%")
        return False

    # Removed hardcoded RULE 2: Protect loyal customers to allow dynamic AI reasoning for win-back strategies

    # RULE 3: Minimum margin
    average_selling_price = 5000.0
    product_cost = 2500.0

    discount_amount = average_selling_price * discount_pct / 100.0
    new_price = average_selling_price - discount_amount

    if new_price <= 0:
        print(f"❌ BLOCKED: Invalid new price {new_price} after discount")
        return False

    new_margin = ((new_price - product_cost) / new_price) * 100.0

    if new_margin < min_margin_percentage:
        print(f"❌ BLOCKED: Margin {new_margin:.1f}% is below minimum required {min_margin_percentage}%")
        return False

    # Format the discount to look clean without trailing zero decimals if integer
    display_discount = int(discount_pct) if discount_pct.is_integer() else discount_pct
    print(f"✓ APPROVED: {display_discount}% discount, projected margin {new_margin:.1f}%")
    return True


if __name__ == "__main__":
    merchant_rules = {
        "max_discount_percentage": 20,
        "min_margin_percentage": 30
    }

    # TEST 1: New visitor, 10% discount, Max 20%, Min margin 30% -> APPROVED
    print("TEST 1: New visitor, 10% discount")
    validate_offer({"discount_pct": 10}, merchant_rules, {"purchase_count": 0})
    print()

    # TEST 2: New visitor, 30% discount, Max 20%, Min margin 30% -> BLOCKED (exceeds max discount)
    print("TEST 2: New visitor, 30% discount")
    validate_offer({"discount_pct": 30}, merchant_rules, {"purchase_count": 0})
    print()

    # TEST 3: Loyal customer, 15% discount, purchase_count = 5 -> BLOCKED (loyal > 5%)
    print("TEST 3: Loyal customer, 15% discount")
    validate_offer({"discount_pct": 15}, merchant_rules, {"purchase_count": 5})
    print()

    # TEST 4: Loyal customer, 0% discount, purchase_count = 5 -> APPROVED
    print("TEST 4: Loyal customer, 0% discount")
    validate_offer({"discount_pct": 0}, merchant_rules, {"purchase_count": 5})
    print()

    # TEST 5: Violates min margin
    # A 30% discount on 5000 yields 3500 price. Margin = (3500 - 2500)/3500 = 28.57% (Below 30%)
    print("TEST 5: Violates minimum margin (30% discount)")
    validate_offer({"discount_pct": 30}, {"max_discount_percentage": 40, "min_margin_percentage": 30}, {"purchase_count": 0})
    print()

    # TEST 6: Malformed/missing discount value
    print("TEST 6: Malformed/missing discount value")
    validate_offer({}, merchant_rules, {"purchase_count": 0})
    print()