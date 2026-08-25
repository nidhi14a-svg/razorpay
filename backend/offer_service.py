import sys
from optimization import generate_deterministic_offer

def generate_personalized_offer(customer: dict, merchant_rules: dict = None) -> dict:
    """
    Unified Customer -> Segment -> Offer pipeline.
    Accepts customer profile and merchant rules.
    Outputs a single structured dictionary with segment and offer.
    """
    # 1. Handle missing merchant rules with sensible defaults
    if merchant_rules is None:
        merchant_rules = {
            "max_discount_percentage": 20.0,
            "min_margin_percentage": 30.0
        }
        
    # Handle missing customer gracefully (defensive check)
    if not isinstance(customer, dict):
        customer = {}
        
    # 2 & 3. Segment customer and Generate offer
    # Note: generate_deterministic_offer handles both segmentation and offer calculation
    offer_result = generate_deterministic_offer(customer, merchant_rules)
    
    # 4. Construct final structured result
    result = {
        "customer": customer,
        "segment": offer_result["segment"],
        "offer": offer_result["offer"],
        "discount_percentage": offer_result["discount_percentage"],
        "reason": offer_result["reason"]
    }
    
    return result

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
        
    print("=" * 60)
    print("PIPELINE DEMO: Customer -> Segment -> Offer")
    print("=" * 60)
    
    merchant_rules = {
        "max_discount_percentage": 20.0,
        "min_margin_percentage": 30.0
    }
    
    test_customers = {
        "loyal": {"name": "Alice", "purchase_count": 5, "days_since_last_purchase": 10},
        "new_visitor": {"name": "Bob", "purchase_count": 0, "cart_status": "browsing"},
        "cart_abandoned": {"name": "Charlie", "cart_status": "abandoned", "days_since_last_purchase": 0},
        "high_value": {"name": "Diana", "lifetime_value": 15000},
        "price_sensitive": {"name": "Eve", "average_order_value": 1000},
        "dormant": {"name": "Frank", "days_since_last_purchase": 100},
        "regular": {"name": "Grace", "days_since_last_purchase": 45}
    }
    
    for label, cust_data in test_customers.items():
        print(f"\n--- Processing {label.upper()} Customer ---")
        result = generate_personalized_offer(cust_data, merchant_rules)
        print("CUSTOMER:")
        for k, v in result["customer"].items():
            print(f"  {k}: {v}")
        print(f"SEGMENT:  {result['segment']}")
        print(f"OFFER:    {result['offer']}")
        print(f"DISCOUNT: {result['discount_percentage']}%")
        print(f"REASON:   {result['reason']}")
