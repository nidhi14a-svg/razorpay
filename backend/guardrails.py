def validate_offer(offer: dict, merchant_rules: dict, customer: dict) -> bool:
    """
    Check if offer respects merchant's business rules.
    
    Returns: True if valid, False if violates rules
    """
    
    discount_pct = offer.get('discount_pct', 0)
    
    # RULE 1: Max discount check
    max_discount = merchant_rules.get('max_discount_percentage', 20)
    if discount_pct > max_discount:
        print(f"❌ BLOCKED: Discount {discount_pct}% exceeds max {max_discount}%")
        return False
    
    # RULE 2: Don't over-discount loyal customers
    is_loyal = customer.get('purchase_count', 0) >= 3
    if is_loyal and discount_pct > 5:
        print(f"❌ BLOCKED: Loyal customer shouldn't get {discount_pct}% off")
        return False
    
    # RULE 3: Check if margin is preserved
    avg_price = 5000  # Assumption
    product_cost = 2500  # Assumption
    discount_amount = avg_price * (discount_pct / 100)
    new_price = avg_price - discount_amount
    
    if new_price > 0:
        new_margin_pct = ((new_price - product_cost) / new_price) * 100
    else:
        new_margin_pct = 0
    
    min_margin = merchant_rules.get('min_margin_percentage', 30)
    if new_margin_pct < min_margin:
        print(f"❌ BLOCKED: Margin {new_margin_pct:.1f}% below minimum {min_margin}%")
        return False
    
    # All checks passed
    print(f"✓ APPROVED: {discount_pct}% off (margin preserved: {new_margin_pct:.1f}%)")
    return True


# Test
if __name__ == "__main__":
    merchant_rules = {
        "max_discount_percentage": 20,
        "min_margin_percentage": 30
    }
    
    # Test 1: Valid offer for new visitor
    print("Test 1: New visitor, 10% off")
    offer1 = {"discount_pct": 10}
    customer1 = {"purchase_count": 0}
    validate_offer(offer1, merchant_rules, customer1)
    print()
    
    # Test 2: Too high discount
    print("Test 2: 30% off (exceeds max 20%)")
    offer2 = {"discount_pct": 30}
    validate_offer(offer2, merchant_rules, customer1)
    print()
    
    # Test 3: Loyal customer shouldn't get discount
    print("Test 3: Loyal customer, 15% off")
    offer3 = {"discount_pct": 15}
    customer3 = {"purchase_count": 5}
    validate_offer(offer3, merchant_rules, customer3)