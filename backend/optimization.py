import sys
from segmentation import segment_customer

def get_max_safe_discount(min_margin_percentage: float) -> float:
    """
    Calculates the maximum discount percentage that still satisfies the
    minimum margin percentage requirement.
    Uses assumptions: average_selling_price = 5000, product_cost = 2500
    """
    average_selling_price = 5000.0
    product_cost = 2500.0
    
    if min_margin_percentage >= 100.0:
        return 0.0
        
    min_price = product_cost / (1.0 - (min_margin_percentage / 100.0))
    
    if min_price >= average_selling_price:
        return 0.0
        
    max_discount = 100.0 * (1.0 - (min_price / average_selling_price))
    return max_discount

def generate_deterministic_offer(customer: dict, merchant_rules: dict) -> dict:
    """
    Given a customer and merchant rules, determines the segment and 
    deterministically generates an appropriate offer respecting business rules.
    """
    # 1. Determine Segment
    segment = segment_customer(customer)
    
    # 2. Extract rules and calculate absolute constraints
    max_discount_rule = float(merchant_rules.get("max_discount_percentage", 20.0))
    min_margin_rule = float(merchant_rules.get("min_margin_percentage", 30.0))
    
    max_safe_discount_margin = get_max_safe_discount(min_margin_rule)
    
    # Absolute max discount allowed by BOTH rules
    absolute_max_discount = min(max_discount_rule, max_safe_discount_margin)
    
    offer_text = ""
    discount_pct = 0.0
    reason = ""
    
    # 3. Generate deterministic offer based on segment
    if segment == "loyal":
        discount_pct = min(5.0, absolute_max_discount)
        offer_text = "VIP Early Access & Loyalty Reward"
        reason = "Reward loyalty without heavily discounting (Guardrail max 5%)"
        
    elif segment == "new_visitor":
        discount_pct = min(10.0, absolute_max_discount)
        offer_text = "Welcome 10% Off Your First Order"
        reason = "Standard acquisition discount for new visitors"
        
    elif segment == "cart_abandoned":
        discount_pct = min(15.0, absolute_max_discount)
        offer_text = "Complete your purchase for 15% off"
        reason = "Urgent recovery of abandoned cart"
        
    elif segment == "high_value":
        discount_pct = 0.0
        offer_text = "Complimentary Premium Concierge Service"
        reason = "Provide premium value to high LTV customers instead of discounting"
        
    elif segment == "price_sensitive":
        # Maximize the discount up to the safe limit
        discount_pct = absolute_max_discount
        offer_text = f"Special Value Deal: {discount_pct:.0f}% Off"
        reason = "Maximize discount to convert price-sensitive shopper safely"
        
    elif segment == "dormant":
        discount_pct = min(20.0, absolute_max_discount)
        offer_text = f"We Miss You! Take {discount_pct:.0f}% Off"
        reason = "Aggressive discount to re-engage dormant customer"
        
    else: # regular
        discount_pct = min(5.0, absolute_max_discount)
        offer_text = "Standard 5% Off"
        reason = "Default promotional offer"
        
    return {
        "segment": segment,
        "offer": offer_text,
        "discount_percentage": discount_pct,
        "reason": reason
    }

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
        
    print("=" * 60)
    print("DETERMINISTIC OFFER GENERATION DEMO")
    print("=" * 60)
    
    merchant_rules = {
        "max_discount_percentage": 20,
        "min_margin_percentage": 30
    }
    
    test_customers = {
        "loyal": {"purchase_count": 5, "days_since_last_purchase": 10},
        "new_visitor": {"purchase_count": 0, "cart_status": "browsing"},
        "cart_abandoned": {"cart_status": "abandoned", "days_since_last_purchase": 0},
        "high_value": {"lifetime_value": 15000},
        "price_sensitive": {"average_order_value": 1000},
        "dormant": {"days_since_last_purchase": 100},
        "regular": {}
    }
    
    for label, cust_data in test_customers.items():
        print(f"\n--- Testing Scenario: {label.upper()} ---")
        result = generate_deterministic_offer(cust_data, merchant_rules)
        print(f"Segment Identified: {result['segment']}")
        print(f"Offer Generated:    {result['offer']}")
        print(f"Discount:           {result['discount_percentage']}%")
        print(f"Reasoning:          {result['reason']}")
