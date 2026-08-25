#!/usr/bin/env python
"""Verify demo customers are segmented correctly"""

from segmentation import segment_customer

demo_customers = [
    {"name": "Rahul Kumar", "purchase_count": 5, "lifetime_value": 15000, "days_since_last_purchase": 5, "average_order_value": 3000, "cart_status": "browsing"},
    {"name": "Priya Singh", "purchase_count": 0, "lifetime_value": 0, "days_since_last_purchase": 999, "average_order_value": 0, "cart_status": "browsing"},
    {"name": "Amit Patel", "purchase_count": 0, "lifetime_value": 0, "days_since_last_purchase": 999, "average_order_value": 0, "cart_status": "abandoned"},
    {"name": "Zara Khan", "purchase_count": 15, "lifetime_value": 50000, "days_since_last_purchase": 2, "average_order_value": 3500, "cart_status": "browsing"},
    {"name": "Vikram Gupta", "purchase_count": 1, "lifetime_value": 5000, "days_since_last_purchase": 90, "average_order_value": 5000, "cart_status": "browsing"},
]

print("Demo Customers - Segment Verification")
print("=" * 50)
for customer in demo_customers:
    segment = segment_customer(customer)
    print(f"{customer['name']}: {segment}")
