def segment_customer(customer: dict) -> str:
    """
    Determine customer segment.
    
    Takes customer data, returns segment name.
    No AI needed - just simple logic.
    """
    
    purchase_count = customer.get('purchase_count', 0)
    days_since_last = customer.get('days_since_last_purchase', 999)
    lifetime_value = customer.get('lifetime_value', 0)
    cart_status = customer.get('cart_status', None)
    aov = customer.get('average_order_value', 0)
    
    # Simple if-else logic
    if purchase_count >= 3 and days_since_last < 30:
        return "loyal"
    
    elif purchase_count == 0 and cart_status == "browsing":
        return "new_visitor"
    
    elif cart_status == "abandoned":
        return "cart_abandoned"
    
    elif lifetime_value > 10000:
        return "high_value"
    
    elif aov > 0 and aov < 2000:
        return "price_sensitive"
    
    elif days_since_last > 60:
        return "dormant"
    
    else:
        return "regular"


# Test
if __name__ == "__main__":
    test_customer = {
        'name': 'Rahul',
        'purchase_count': 5,
        'lifetime_value': 15000,
        'days_since_last_purchase': 5,
        'average_order_value': 3000,
        'cart_status': 'browsing'
    }
    
    segment = segment_customer(test_customer)
    print(f"Customer is: {segment}")