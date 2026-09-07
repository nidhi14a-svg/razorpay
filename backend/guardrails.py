import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def validate_merchant_guardrails(rules: dict) -> tuple[bool, str]:
    """
    Validates merchant guardrail inputs before saving.
    Returns (True, "") if valid, or (False, error_message) if invalid.
    """
    if not isinstance(rules, dict):
        return False, "Guardrail rules must be a valid object."

    # 1. Maximum Discount Percentage (0 to 100)
    max_discount = rules.get("max_discount_percentage")
    if max_discount is None:
        return False, "Maximum discount percentage is required."
    try:
        max_discount = float(max_discount)
        if max_discount < 0 or max_discount > 100:
            return False, "Maximum discount percentage must be between 0% and 100%."
    except (ValueError, TypeError):
        return False, "Maximum discount percentage must be a valid number."

    # 2. Minimum Order Value (>= 0)
    min_order = rules.get("min_order_value")
    if min_order is not None:
        try:
            min_order = float(min_order)
            if min_order < 0:
                return False, "Minimum order value cannot be negative."
        except (ValueError, TypeError):
            return False, "Minimum order value must be a valid number."

    # 3. Maximum Campaign Budget (optional, >= 0)
    budget = rules.get("max_campaign_budget")
    if budget is not None and budget != "":
        try:
            budget = float(budget)
            if budget < 0:
                return False, "Maximum campaign budget cannot be negative."
        except (ValueError, TypeError):
            return False, "Maximum campaign budget must be a valid number."

    # 4. Customer Contact Frequency (optional, >= 0)
    freq = rules.get("contact_frequency_days")
    if freq is not None and freq != "":
        try:
            freq = int(freq)
            if freq < 0:
                return False, "Contact frequency days cannot be negative."
        except (ValueError, TypeError):
            return False, "Contact frequency days must be a valid integer."

    # 5. Minimum Margin Percentage (required, 0 to 100)
    min_margin = rules.get("min_margin_percentage")
    if min_margin is None:
        return False, "Minimum margin percentage is required."
    try:
        min_margin = float(min_margin)
        if min_margin < 0 or min_margin > 100:
            return False, "Minimum margin percentage must be between 0% and 100%."
    except (ValueError, TypeError):
        return False, "Minimum margin percentage must be a valid number."

    return True, ""


def validate_offer(offer: dict, merchant_rules: dict, customer: dict) -> bool:
    """
    Validates an AI-generated offer against merchant business rules.
    Returns True if approved, False if blocked.
    """
    # Defensive input validation
    if not isinstance(offer, dict) or not isinstance(merchant_rules, dict) or not isinstance(customer, dict):
        print("❌ BLOCKED: Malformed input - Missing or invalid dictionaries")
        return False

    if not merchant_rules:
        print("❌ BLOCKED: Merchant guardrail rules are not present")
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
        max_discount_percentage = float(merchant_rules.get("max_discount_percentage", 20.0))
        min_margin_percentage = float(merchant_rules.get("min_margin_percentage", 25.0))
    except (TypeError, ValueError):
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

    # RULE 2: High-Value Customer Protection
    # If high_value_customer_protection is enabled, prefer non-discount incentives for loyal/high-value customers
    high_value_protection = merchant_rules.get("high_value_customer_protection", True)
    lifetime_value = float(customer.get("lifetime_value", 0.0) or 0.0)
    is_high_value = purchase_count >= 5 or lifetime_value >= 10000.0

    if high_value_protection and is_high_value and discount_pct > 5.0:
        print(f"❌ BLOCKED: High-value customer protection active - discount {discount_pct}% exceeds safe 5% cap")
        return False

    # RULE 3: Free Shipping Check
    if offer.get("free_shipping", False) and not merchant_rules.get("free_shipping_allowed", True):
        print("❌ BLOCKED: Free shipping recommended but prohibited by merchant rules")
        return False

    # RULE 4: Minimum margin
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