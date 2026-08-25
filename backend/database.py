from pymongo import MongoClient
from dotenv import load_dotenv
import os
import sys

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

# Connect to MongoDB
MONGODB_URI = os.getenv("MONGODB_URI")

# Validate MongoDB URI is configured
if not MONGODB_URI or "your_mongodb_connection_string" in MONGODB_URI.lower():
    print("❌ ERROR: MONGODB_URI not configured in .env")
    print("   Please set MONGODB_URI to your MongoDB Atlas connection string")
    print("   Format: mongodb+srv://username:password@cluster.mongodb.net/database")
    sys.exit(1)

try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    # Test connection
    client.admin.command('ping')
except Exception as e:
    print(f"❌ ERROR: Could not connect to MongoDB")
    print(f"   Details: {e}")
    sys.exit(1)

db = client["smart_segmentation"]

# Collections (like tables in SQL)
merchants_collection = db["merchants"]
customers_collection = db["customers"]
campaigns_collection = db["campaigns"]
offers_collection = db["offers"]
orders_collection = db["orders"]

def init_indexes():
    """Create useful indexes on collections to optimize queries."""
    try:
        offers_collection.create_index("offer_id", unique=True)
        offers_collection.create_index("merchant_id")
        offers_collection.create_index("status")
        
        orders_collection.create_index("offer_id")
        orders_collection.create_index("razorpay_order_id", unique=True)
        orders_collection.create_index("razorpay_payment_id")
        orders_collection.create_index("payment_status")
        print("✓ Database indexes initialized successfully")
    except Exception as e:
        print(f"⚠️ Warning: Failed to initialize indexes: {e}")

# Initialize indexes when database is loaded
init_indexes()

print("✓ Database connected to MongoDB")