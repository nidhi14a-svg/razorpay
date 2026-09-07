import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def segment_customer(customer: dict, thresholds: dict = None, vip_threshold: float = None, **kwargs) -> str:
    """
    Determine customer segment based on deterministic business logic and dataset thresholds.
    Primary Segments:
      - VIP: High lifetime value and frequent purchases
      - Loyal: Frequent purchases and recent activity
      - At Risk: Previously valuable but inactive for an extended period
      - Inactive: Very long time since last purchase (> 180 days) or no purchase history
      - Regular: Normal purchasing behaviour
    Also supports real-time web signals (cart_abandoned, new_visitor) when present.
    """
    purchase_count = customer.get('purchase_count', 0)
    days_since_last = customer.get('days_since_last_purchase', 999)
    cart_status = customer.get('cart_status', "")
    lifetime_value = customer.get('lifetime_value', 0.0)
    aov = customer.get('average_order_value', 0.0)
    has_orders = customer.get('has_orders', purchase_count > 0)
    
    # 1. Real-time cart abandoner
    if cart_status == "abandoned":
        return "cart_abandoned"

    # 2. New visitor (0 purchases, active browsing)
    if purchase_count == 0 and cart_status == "browsing":
        return "new_visitor"

    # Calibrate thresholds from dataset or sensible defaults
    if vip_threshold is not None:
        p75_ltv = float(vip_threshold)
    else:
        p75_ltv = float((thresholds or {}).get("p75_ltv", 500.0))
    p50_ltv = float((thresholds or {}).get("p50_ltv", 150.0))

    # 3. Inactive: No order history, or very old purchase (> 180 days)
    if not has_orders or purchase_count == 0 or days_since_last > 180:
        return "inactive"

    # 4. VIP: High lifetime value AND frequent purchases (or top-tier single order LTV)
    if (lifetime_value >= 10000) or (lifetime_value >= p75_ltv and purchase_count >= 2) or (lifetime_value >= max(1000.0, p75_ltv * 1.5)):
        return "vip"

    # 5. Loyal: Frequent purchases and recent activity (<= 60 days)
    if purchase_count >= 2 and days_since_last <= 60:
        return "loyal"

    # 6. At Risk: Previously valuable (LTV >= median or 2+ purchases) but inactive for 60 to 180 days
    if (lifetime_value >= p50_ltv or purchase_count >= 2) and (60 < days_since_last <= 180):
        return "at_risk"

    # 7. Price Sensitive: Low AOV with browsing
    if 0 < aov < 2000 and cart_status == "browsing":
        return "price_sensitive"

    # 8. Regular: Normal active purchasing behaviour
    return "regular"

if __name__ == "__main__":
    test_customers = [
        {
            "name": "VIP Victor",
            "purchase_count": 4,
            "days_since_last_purchase": 15,
            "lifetime_value": 2500,
            "average_order_value": 625
        },
        {
            "name": "Loyal Larry",
            "purchase_count": 3,
            "days_since_last_purchase": 10,
            "lifetime_value": 450,
            "average_order_value": 150
        },
        {
            "name": "At-Risk Amy",
            "purchase_count": 3,
            "days_since_last_purchase": 120,
            "lifetime_value": 600,
            "average_order_value": 200
        },
        {
            "name": "Inactive Ian",
            "purchase_count": 1,
            "days_since_last_purchase": 250,
            "lifetime_value": 100,
            "average_order_value": 100
        },
        {
            "name": "Regular Rachel",
            "purchase_count": 1,
            "days_since_last_purchase": 35,
            "lifetime_value": 120,
            "average_order_value": 120
        }
    ]

    print("--- Testing Deterministic Segmentation ---")
    for cust in test_customers:
        seg = segment_customer(cust)
        print(f"{cust['name']:<20} -> Segment: {seg}")