"""
Run this to create demo merchant + customers in MongoDB.
Provides a realistic, diverse dataset for testing the AI and segmentation logic.
"""

import uuid
import random
from datetime import datetime, timezone
from database import merchants_collection, customers_collection, campaigns_collection, offers_collection, optimizations_collection
from segmentation import segment_customer

def clear_demo_data(merchant_id="demo_merchant_001"):
    """Remove existing demo data to ensure a clean state."""
    print(f"Clearing existing data for merchant: {merchant_id}")
    customers_collection.delete_many({"merchant_id": merchant_id})
    campaigns_collection.delete_many({"merchant_id": merchant_id})
    offers_collection.delete_many({"merchant_id": merchant_id})
    optimizations_collection.delete_many({"merchant_id": merchant_id})
    merchants_collection.delete_many({"merchant_id": merchant_id})

def setup_demo_data(merchant_id="demo_merchant_001"):
    """Create demo merchant and a diverse set of realistic customers."""
    
    # 1. Clean up existing demo state
    clear_demo_data(merchant_id)
    
    print("Setting up realistic demo data...")
    
    # 2. Create demo merchant
    merchant = {
        "merchant_id": merchant_id,
        "email": "demo@example.com",
        "password": "demo123", # For demo purposes
        "business_name": "Summer Store (Demo)",
        "rules": {
            "max_discount_percentage": 25,
            "min_margin_percentage": 30,
            "budget_per_week": 50000
        }
    }
    
    merchants_collection.insert_one(merchant)
    print("✓ Demo merchant created")
    
    # 3. Generate Diverse Customers
    # We want ~40 customers. Let's create groups of archetypes to ensure diversity.
    archetypes = [
        # Loyal/High Value (Frequent purchases, high AOV, recent)
        {"count": 8, "purchases": (10, 25), "aov": (2000, 5000), "recency": (1, 15), "cart": ["purchased", "browsing"]},
        # New/Recent (1-2 purchases, recent)
        {"count": 10, "purchases": (1, 2), "aov": (500, 1500), "recency": (1, 10), "cart": ["browsing", "purchased"]},
        # Dormant/At-Risk (High/Med purchases, but long time ago)
        {"count": 7, "purchases": (3, 10), "aov": (1000, 3000), "recency": (60, 150), "cart": ["abandoned", "browsing"]},
        # Cart Abandoners (Various purchases, recently abandoned cart)
        {"count": 7, "purchases": (0, 5), "aov": (800, 2500), "recency": (1, 30), "cart": ["abandoned"]},
        # Price Sensitive/Low Value (Low AOV, infrequent)
        {"count": 8, "purchases": (1, 4), "aov": (200, 600), "recency": (15, 60), "cart": ["browsing", "abandoned"]}
    ]
    
    names = [
        "Aarav", "Vihaan", "Aditya", "Sai", "Arjun", "Reyansh", "Ayaan", "Krishna", "Ishaan", "Shaurya",
        "Ananya", "Diya", "Avni", "Kavya", "Saanvi", "Myra", "Aadhya", "Riya", "Kiara", "Prisha",
        "Rohan", "Kabir", "Dhruv", "Rudra", "Vivaan", "Ira", "Sara", "Meera", "Sia", "Navya",
        "Priya", "Rahul", "Amit", "Neha", "Vikram", "Sneha", "Karan", "Pooja", "Raj", "Nisha"
    ]
    surnames = ["Kumar", "Singh", "Sharma", "Patel", "Gupta", "Reddy", "Rao", "Jain", "Desai", "Joshi", "Verma", "Kapoor"]

    demo_customers = []
    customer_idx = 1
    
    for archetype in archetypes:
        for _ in range(archetype["count"]):
            purchase_count = random.randint(*archetype["purchases"])
            aov = random.uniform(*archetype["aov"])
            lifetime_value = purchase_count * aov
            recency = random.randint(*archetype["recency"])
            cart_status = random.choice(archetype["cart"])
            
            first_name = random.choice(names)
            last_name = random.choice(surnames)
            
            customer = {
                "id": f"demo_cust_{customer_idx:03d}",
                "customer_id": f"demo_cust_{customer_idx:03d}", # For backwards compatibility if any
                "merchant_id": merchant_id,
                "name": f"{first_name} {last_name}",
                "email": f"{first_name.lower()}.{last_name.lower()}@example.com",
                "purchase_count": purchase_count,
                "lifetime_value": round(lifetime_value, 2),
                "days_since_last_purchase": recency,
                "average_order_value": round(aov, 2),
                "cart_status": cart_status
            }
            demo_customers.append(customer)
            customer_idx += 1
            
    # Randomize the order
    random.shuffle(demo_customers)
            
    # 4. Assign segments and aggregate stats
    print(f"\nAssigning segments to {len(demo_customers)} customers:")
    segments_found = set()
    for customer in demo_customers:
        customer['segment'] = segment_customer(customer)
        segments_found.add(customer['segment'])
    
    try:
        customers_collection.insert_many(demo_customers)
        print(f"✓ Created {len(demo_customers)} diverse demo customers")
        print(f"✓ Identified {len(segments_found)} distinct segments")
        
        # 5. Create Demo Campaigns
        print("\nCreating demo campaigns and offers...")
        campaign_1_id = str(uuid.uuid4())
        campaign_2_id = str(uuid.uuid4())
        
        campaigns = [
            {
                "campaign_id": campaign_1_id,
                "merchant_id": merchant_id,
                "name": "Summer Splash Retention",
                "description": "Retain loyal and dormant customers with summer specials.",
                "target_segment": "auto",
                "status": "ACTIVE",
                "target_segments": ["loyal", "dormant"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "campaign_id": campaign_2_id,
                "merchant_id": merchant_id,
                "name": "Abandoned Cart Recovery",
                "description": "Aggressive discounts to recover abandoned carts.",
                "target_segment": "cart_abandoned",
                "status": "ACTIVE",
                "target_segments": ["cart_abandoned"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        campaigns_collection.insert_many(campaigns)
        
        # 6. Create Demo Offers
        demo_offers = []
        for customer in demo_customers:
            seg = customer['segment']
            if seg in ["loyal", "dormant"]:
                demo_offers.append({
                    "offer_id": str(uuid.uuid4()),
                    "campaign_id": campaign_1_id,
                    "merchant_id": merchant_id,
                    "customer_id": customer["id"],
                    "customer_segment": seg,
                    "offer_description": f"Exclusive 15% off summer collection for {seg} customers.",
                    "discount_percentage": 15.0,
                    "explanation": "Targeted discount for retention.",
                    "status": "OFFER_CREATED",
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
            elif seg == "cart_abandoned":
                demo_offers.append({
                    "offer_id": str(uuid.uuid4()),
                    "campaign_id": campaign_2_id,
                    "merchant_id": merchant_id,
                    "customer_id": customer["id"],
                    "customer_segment": seg,
                    "offer_description": "Complete your purchase and get 20% off your cart!",
                    "discount_percentage": 20.0,
                    "explanation": "High discount to recover cart.",
                    "status": "OFFER_CREATED",
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                
        if demo_offers:
            offers_collection.insert_many(demo_offers)
            
        # 7. Create Demo Optimization
        optimization_doc = {
            "optimization_id": str(uuid.uuid4()),
            "campaign_id": campaign_1_id,
            "merchant_id": merchant_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "campaign_metrics_snapshot": {"conversion_rate": 0.05, "total_revenue": 1500},
            "segment_metrics_snapshot": [],
            "recommendations": [
                {
                    "type": "discount_adjustment",
                    "segment": "dormant",
                    "recommended_change": "Increase discount to 20%",
                    "reason": "Conversion rate is too low for dormant customers.",
                    "priority": "high",
                    "status": "GENERATED"
                }
            ],
            "overall_assessment": "The campaign is performing moderately, but dormant customers need a stronger incentive.",
            "status": "GENERATED"
        }
        optimizations_collection.insert_one(optimization_doc)
        
    except Exception as e:
        print(f"❌ Error inserting customers/campaigns: {e}")
        raise
    
    print("\n✅ Demo data setup complete!")
    
    return {
        "status": "success",
        "customers_count": len(demo_customers),
        "segments_count": len(segments_found),
        "merchant_id": merchant_id
    }

if __name__ == "__main__":
    setup_demo_data()