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
    print("   Please set MONGODB_URI to your MongoDB Atlas connection string or local MongoDB URI")
    print("   Format: mongodb+srv://username:password@cluster.mongodb.net/smart_segmentation?retryWrites=true&w=majority")
    sys.exit(1)

# Configure TLS/SSL certificate authority for cloud databases (MongoDB Atlas)
client_kwargs = {
    "serverSelectionTimeoutMS": int(os.getenv("MONGODB_TIMEOUT_MS", "5000"))
}
try:
    import certifi
    if "mongodb+srv://" in MONGODB_URI or "ssl=true" in MONGODB_URI.lower() or "tls=true" in MONGODB_URI.lower():
        client_kwargs["tlsCAFile"] = certifi.where()
except ImportError:
    pass

try:
    client = MongoClient(MONGODB_URI, **client_kwargs)
    # Test connection
    client.admin.command('ping')
except Exception as e:
    print(f"❌ ERROR: Could not connect to MongoDB at {MONGODB_URI.split('@')[-1] if '@' in MONGODB_URI else 'specified host'}")
    print(f"   Details: {e}")
    print("   Tip: If using MongoDB Atlas, check Network Access / IP Access List (allow access from anywhere 0.0.0.0/0 for cloud hosting).")
    sys.exit(1)

# Resolve target database: explicit DB_NAME env var -> URI database name -> fallback 'smart_segmentation'
db_name = os.getenv("DB_NAME", os.getenv("MONGODB_DB_NAME"))
if not db_name:
    try:
        db = client.get_default_database()
        if db is None:
            db = client["smart_segmentation"]
    except Exception:
        db = client["smart_segmentation"]
else:
    db = client[db_name]

# Collections (like tables in SQL)
merchants_collection = db["merchants"]
customers_collection = db["customers"]
campaigns_collection = db["campaigns"]
offers_collection = db["offers"]
orders_collection = db["orders"]
optimizations_collection = db["optimizations"]
optimization_executions_collection = db["optimization_executions"]
feedback_collection = db["feedback"]
agent_runs_collection = db["agent_runs"]
campaign_executions_collection = db["campaign_executions"]
def init_indexes():
    """Create useful indexes on collections to optimize queries."""
    try:
        offers_collection.create_index("offer_id", unique=True)
        offers_collection.create_index("merchant_id")
        offers_collection.create_index("status")
        offers_collection.create_index("campaign_id")
        
        campaigns_collection.create_index("campaign_id", unique=True)
        campaigns_collection.create_index("merchant_id")
        campaigns_collection.create_index("status")
        
        orders_collection.create_index("offer_id")
        orders_collection.create_index("razorpay_order_id", unique=True)
        orders_collection.create_index("razorpay_payment_id")
        orders_collection.create_index("payment_status")
        
        optimizations_collection.create_index("optimization_id", unique=True)
        optimizations_collection.create_index("campaign_id")
        optimizations_collection.create_index("merchant_id")
        
        optimization_executions_collection.create_index("execution_id", unique=True)
        optimization_executions_collection.create_index("optimization_id")
        optimization_executions_collection.create_index("merchant_id")
        
        feedback_collection.create_index("feedback_id", unique=True)
        feedback_collection.create_index("optimization_id", unique=True)
        feedback_collection.create_index("campaign_id")
        feedback_collection.create_index("merchant_id")
        
        agent_runs_collection.create_index("agent_run_id", unique=True)
        agent_runs_collection.create_index("merchant_id")
        
        campaign_executions_collection.create_index("execution_id", unique=True)
        campaign_executions_collection.create_index("campaign_id")
        campaign_executions_collection.create_index("merchant_id")
        
        customers_collection.create_index("merchant_id")
        customers_collection.create_index([("merchant_id", 1), ("segment", 1)])
        customers_collection.create_index([("merchant_id", 1), ("id", 1)])
        
        print("✓ Database indexes initialized successfully")
    except Exception as e:
        print(f"⚠️ Warning: Failed to initialize indexes: {e}")

# Initialize indexes when database is loaded
init_indexes()

print("✓ Database connected to MongoDB")