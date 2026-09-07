from database import customers_collection, merchants_collection

print("=" * 60)
print("MONGODB CUSTOMER & MERCHANT AUDIT")
print("=" * 60)

total_cust = customers_collection.count_documents({})
print(f"Total customers across all DB: {total_cust}")

pipeline = [
    {"$group": {"_id": "$merchant_id", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
]
results = list(customers_collection.aggregate(pipeline))
print(f"\nBreakdown by merchant_id ({len(results)} distinct merchants):")
for r in results:
    mid = r["_id"]
    cnt = r["count"]
    m = merchants_collection.find_one({"merchant_id": mid})
    email = m.get("email") if m else "NO_MERCHANT_DOC"
    bname = m.get("business_name") if m else ""
    print(f" - merchant_id: {mid} | count: {cnt} | email: {email} | business: {bname}")

# Look for 96000 records
olist_merchant = merchants_collection.find_one({"email": "nidhi14a@gmail.com"})
if olist_merchant:
    mid = olist_merchant["merchant_id"]
    c_count = customers_collection.count_documents({"merchant_id": mid})
    print(f"\nSpecific check for nidhi14a@gmail.com ({mid}): {c_count} customers in MongoDB")
