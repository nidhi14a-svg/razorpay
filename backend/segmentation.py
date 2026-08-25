def segment_customer(customer: dict) -> str:
    """
    Determine customer segment based on deterministic business logic.
    """
    purchase_count = customer.get('purchase_count', 0)
    days_since_last = customer.get('days_since_last_purchase', 999)
    cart_status = customer.get('cart_status', "")
    lifetime_value = customer.get('lifetime_value', 0)
    aov = customer.get('average_order_value', 0)
    
    if purchase_count >= 3 and days_since_last < 30:
        return "loyal"
        
    if purchase_count == 0 and cart_status == "browsing":
        return "new_visitor"
        
    if cart_status == "abandoned" and days_since_last < 1:
        return "cart_abandoned"
        
    if lifetime_value > 10000:
        return "high_value"
        
    if aov > 0 and aov < 2000:
        return "price_sensitive"
        
    if days_since_last > 60:
        return "dormant"
        
    return "regular"

if __name__ == "__main__":
    test_customers = [
        {
            "name": "Loyal Larry",
            "purchase_count": 5,
            "days_since_last_purchase": 10,
            "cart_status": "browsing",
            "lifetime_value": 5000,
            "average_order_value": 1000
        },
        {
            "name": "Newbie Nancy",
            "purchase_count": 0,
            "days_since_last_purchase": 999,
            "cart_status": "browsing",
            "lifetime_value": 0,
            "average_order_value": 0
        },
        {
            "name": "Abandoner Andy",
            "purchase_count": 1,
            "days_since_last_purchase": 0,
            "cart_status": "abandoned",
            "lifetime_value": 100,
            "average_order_value": 100
        },
        {
            "name": "High Value Harriet",
            "purchase_count": 2,
            "days_since_last_purchase": 45,
            "cart_status": "browsing",
            "lifetime_value": 15000,
            "average_order_value": 7500
        },
        {
            "name": "Price Sensitive Pete",
            "purchase_count": 1,
            "days_since_last_purchase": 40,
            "cart_status": "browsing",
            "lifetime_value": 500,
            "average_order_value": 500
        },
        {
            "name": "Dormant Dan",
            "purchase_count": 1,
            "days_since_last_purchase": 100,
            "cart_status": "browsing",
            "lifetime_value": 3000,
            "average_order_value": 3000
        },
        {
            "name": "Regular Rachel",
            "purchase_count": 1,
            "days_since_last_purchase": 45,
            "cart_status": "browsing",
            "lifetime_value": 5000,
            "average_order_value": 5000
        }
    ]

    print("--- Testing Segmentation Logic ---")
    for customer in test_customers:
        segment = segment_customer(customer)
        print(f"Customer: {customer['name']:<25} -> Segment: {segment}")