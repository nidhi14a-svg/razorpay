from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

# Connect to MongoDB
MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)
db = client["smart_segmentation"]

# Collections (like tables in SQL)
merchants_collection = db["merchants"]
customers_collection = db["customers"]
campaigns_collection = db["campaigns"]

print("✓ Database connected to MongoDB")