"""
Run this ONCE to create demo merchant + customers in MongoDB.
"""

from database import merchants_collection, customers_collection
from segmentation import segment_customer

def setup_demo_data():
    """Create demo merchant and customers"""
    
    print("Setting up demo data...")
    
    # Create demo merchant
    merchant = {
        "merchant_id": "demo_merchant_001",
        "email": "demo@example.com",
        "password": "demo123",
        "business_name": "Summer Store",
        "rules": {
            "max_discount_percentage": 20,
            "min_margin_percentage": 30,
            "budget_per_week": 25000
        }
    }
    
    try:
        merchants_collection.insert_one(merchant)
        print("✓ Demo merchant created")
    except Exception as e:
        if "duplicate key" in str(e).lower():
            print("⚠ Demo merchant already exists (skipping insert)")
        else:
            raise
    
    # Create demo customers
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
    
    # Add segment to each customer
    print("\nAssigning customer segments:")
    for customer in demo_customers:
        customer['segment'] = segment_customer(customer)
        print(f"  • {customer['name']}: {customer['segment']}")
    
    try:
        customers_collection.insert_many(demo_customers)
        print(f"✓ Created {len(demo_customers)} demo customers")
    except Exception as e:
        if "duplicate key" in str(e).lower():
            print(f"⚠ Some customers already exist (partial insert)")
        else:
            raise
    
    print("\n✅ Demo data setup complete!")
    print("\nDemo Login:")
    print("  Email: demo@example.com")
    print("  Password: demo123")

if __name__ == "__main__":
    setup_demo_data()