#!/usr/bin/env python
"""
Test segmentation logic against demo customers
"""

from segmentation import segment_customer

# Test all demo customers
demo_customers = [
    {
        "customer_id": "cust_001",
        "merchant_id": "demo_merchant_001",
        "name": "Rahul Kumar",
        "email": "rahul@gmail.com",
        "purchase_count": 5,
        "lifetime_value": 15000,
        "days_since_last_purchase": 5,
        "average_order_value": 3000,
        "cart_status": "browsing"
    },
    {
        "customer_id": "cust_002",
        "merchant_id": "demo_merchant_001",
        "name": "Priya Singh",
        "email": "priya@gmail.com",
        "purchase_count": 0,
        "lifetime_value": 0,
        "days_since_last_purchase": 999,
        "average_order_value": 0,
        "cart_status": "browsing"
    },
    {
        "customer_id": "cust_003",
        "merchant_id": "demo_merchant_001",
        "name": "Amit Patel",
        "email": "amit@gmail.com",
        "purchase_count": 0,
        "lifetime_value": 0,
        "days_since_last_purchase": 999,
        "average_order_value": 0,
        "cart_status": "abandoned"
    },
    {
        "customer_id": "cust_004",
        "merchant_id": "demo_merchant_001",
        "name": "Zara Khan",
        "email": "zara@gmail.com",
        "purchase_count": 15,
        "lifetime_value": 50000,
        "days_since_last_purchase": 2,
        "average_order_value": 3500,
        "cart_status": "browsing"
    },
    {
        "customer_id": "cust_005",
        "merchant_id": "demo_merchant_001",
        "name": "Vikram Gupta",
        "email": "vikram@gmail.com",
        "purchase_count": 1,
        "lifetime_value": 5000,
        "days_since_last_purchase": 90,
        "average_order_value": 5000,
        "cart_status": "browsing"
    }
]

# Test each customer
print("=" * 70)
print("SEGMENTATION TEST - Demo Customers")
print("=" * 70)

for customer in demo_customers:
    segment = segment_customer(customer)
    print(f"\n{customer['name']}:")
    print(f"  ID: {customer['customer_id']}")
    print(f"  Purchases: {customer['purchase_count']}, LTV: ₹{customer['lifetime_value']}, Days Since Last: {customer['days_since_last_purchase']}")
    print(f"  AOV: ₹{customer['average_order_value']}, Cart Status: {customer['cart_status']}")
    print(f"  → Segment: {segment}")

# Test edge cases and all 7 segments
print("\n" + "=" * 70)
print("EDGE CASE TESTS - All 7 Segments")
print("=" * 70)

edge_cases = [
    {
        "name": "loyal",
        "description": "3+ purchases, recent (< 30 days)",
        "data": {
            "purchase_count": 5,
            "days_since_last_purchase": 15,
            "lifetime_value": 5000,
            "average_order_value": 1000,
            "cart_status": "browsing"
        }
    },
    {
        "name": "new_visitor",
        "description": "0 purchases, browsing",
        "data": {
            "purchase_count": 0,
            "days_since_last_purchase": 999,
            "lifetime_value": 0,
            "average_order_value": 0,
            "cart_status": "browsing"
        }
    },
    {
        "name": "cart_abandoned",
        "description": "Abandoned cart (takes priority over other conditions)",
        "data": {
            "purchase_count": 10,
            "days_since_last_purchase": 5,
            "lifetime_value": 50000,
            "average_order_value": 5000,
            "cart_status": "abandoned"
        }
    },
    {
        "name": "high_value",
        "description": "LTV > 10000 (and not matching earlier conditions)",
        "data": {
            "purchase_count": 1,
            "days_since_last_purchase": 999,
            "lifetime_value": 25000,
            "average_order_value": 3000,
            "cart_status": "browsing"
        }
    },
    {
        "name": "price_sensitive",
        "description": "AOV between 1 and 1999 (and not matching earlier conditions)",
        "data": {
            "purchase_count": 1,
            "days_since_last_purchase": 40,
            "lifetime_value": 500,
            "average_order_value": 500,
            "cart_status": "browsing"
        }
    },
    {
        "name": "dormant",
        "description": "No purchase in 60+ days (and not matching earlier conditions)",
        "data": {
            "purchase_count": 2,
            "days_since_last_purchase": 90,
            "lifetime_value": 2000,
            "average_order_value": 1000,
            "cart_status": "browsing"
        }
    },
    {
        "name": "regular",
        "description": "Doesn't match any other criteria (fallback) - moderate AOV >= 2000",
        "data": {
            "purchase_count": 2,
            "days_since_last_purchase": 45,
            "lifetime_value": 3000,
            "average_order_value": 2500,
            "cart_status": "browsing"
        }
    }
]

for test in edge_cases:
    result = segment_customer(test["data"])
    status = "✓" if result == test["name"] else "✗"
    print(f"\n{status} {test['name'].upper()}")
    print(f"  Description: {test['description']}")
    print(f"  Expected: {test['name']}, Got: {result}")

print("\n" + "=" * 70)
print("SEGMENTATION TEST COMPLETE")
print("=" * 70)
