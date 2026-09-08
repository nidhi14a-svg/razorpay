#!/usr/bin/env python3
"""
seed_demo_data.py
Production-ready, idempotent demo data seeding script for MongoDB Atlas / Local MongoDB.

Usage:
  python seed_demo_data.py           # Safe idempotent seed (seeds only if missing)
  python seed_demo_data.py --verify  # Check existing demo data counts without modifying
  python seed_demo_data.py --force   # Force clean reset and re-seed demo data
"""

import sys
import argparse
from datetime import datetime, timezone

# Ensure utf-8 output encoding for terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from database import (
    merchants_collection,
    customers_collection,
    campaigns_collection,
    offers_collection,
    optimizations_collection,
    MONGODB_URI,
    db_name
)
from demo import setup_demo_data, clear_demo_data

DEMO_MERCHANT_ID = "demo_merchant_001"
DEMO_EMAIL = "demo@example.com"

def mask_mongo_uri(uri: str) -> str:
    """Mask password in MongoDB URI for safe logging."""
    if not uri:
        return "Not configured"
    if "@" in uri:
        try:
            prefix, rest = uri.split("://", 1)
            creds, host_part = rest.split("@", 1)
            user = creds.split(":", 1)[0] if ":" in creds else creds
            return f"{prefix}://{user}:****@{host_part}"
        except Exception:
            return "mongodb+srv://****"
    return uri

def audit_demo_data(merchant_id: str = DEMO_MERCHANT_ID) -> dict:
    """Audit counts of demo records across all relevant collections."""
    merchant = merchants_collection.find_one({"merchant_id": merchant_id})
    customers_count = customers_collection.count_documents({"merchant_id": merchant_id})
    campaigns_count = campaigns_collection.count_documents({"merchant_id": merchant_id})
    offers_count = offers_collection.count_documents({"merchant_id": merchant_id})
    optimizations_count = optimizations_collection.count_documents({"merchant_id": merchant_id})

    # Breakdown by segment
    segment_pipeline = [
        {"$match": {"merchant_id": merchant_id}},
        {"$group": {"_id": "$segment", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    segments = list(customers_collection.aggregate(segment_pipeline))

    return {
        "merchant_exists": bool(merchant),
        "merchant_email": merchant.get("email") if merchant else None,
        "business_name": merchant.get("business_name") if merchant else None,
        "onboarding_completed": merchant.get("onboarding_completed") if merchant else None,
        "customers_count": customers_count,
        "campaigns_count": campaigns_count,
        "offers_count": offers_count,
        "optimizations_count": optimizations_count,
        "segments": {s["_id"]: s["count"] for s in segments if s["_id"]}
    }

def print_audit_report(audit: dict):
    print("=" * 60)
    print("DEMO DATA AUDIT REPORT")
    print("=" * 60)
    print(f"Target Merchant ID   : {DEMO_MERCHANT_ID}")
    print(f"Merchant Document    : {'✓ Present' if audit['merchant_exists'] else '✗ Missing'}")
    if audit["merchant_exists"]:
        print(f" - Email             : {audit['merchant_email']}")
        print(f" - Business Name     : {audit['business_name']}")
        print(f" - Onboarding Done   : {audit['onboarding_completed']}")
    print(f"Customers Count      : {audit['customers_count']}")
    if audit["segments"]:
        print(f" - Segments Breakdown: {audit['segments']}")
    print(f"Campaigns Count      : {audit['campaigns_count']}")
    print(f"Offers Count         : {audit['offers_count']}")
    print(f"Optimizations Count  : {audit['optimizations_count']}")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="RAZZZ Safe Demo Data Seeding Tool")
    parser.add_argument("--force", action="store_true", help="Force wipe and re-seed of demo data")
    parser.add_argument("--verify", action="store_true", help="Audit and verify demo data status only")
    args = parser.parse_args()

    print("\n🚀 RAZZZ Demo Data Seeding Utility")
    print(f"Connected Database : {db_name}")
    print(f"Target URI         : {mask_mongo_uri(MONGODB_URI)}")

    initial_audit = audit_demo_data(DEMO_MERCHANT_ID)

    if args.verify:
        print_audit_report(initial_audit)
        is_ready = initial_audit["merchant_exists"] and initial_audit["customers_count"] > 0
        if is_ready:
            print("✅ Status: Demo account is ready for login (demo@example.com / demo123).")
            sys.exit(0)
        else:
            print("⚠️ Status: Demo data is missing or incomplete in this database.")
            sys.exit(1)

    if args.force:
        print(f"\n⚠️  --force flag detected: Resetting and re-seeding demo data for {DEMO_MERCHANT_ID}...")
        result = setup_demo_data(merchant_id=DEMO_MERCHANT_ID, idempotent=False)
    else:
        # Idempotent check
        if initial_audit["merchant_exists"] and initial_audit["customers_count"] > 0:
            print(f"\n✓ Demo data already exists ({initial_audit['customers_count']} customers found).")
            print("  No changes made (Idempotent run). Use --force to re-seed if necessary.")
            print_audit_report(initial_audit)
            print("✅ Demo login is operational: demo@example.com / demo123\n")
            sys.exit(0)

        print(f"\n🌱 Demo data not found. Seeding initial dataset for {DEMO_MERCHANT_ID}...")
        result = setup_demo_data(merchant_id=DEMO_MERCHANT_ID, idempotent=False)

    final_audit = audit_demo_data(DEMO_MERCHANT_ID)
    print_audit_report(final_audit)
    print("✅ Demo seeding completed successfully!")
    print(f"Login Credentials : {DEMO_EMAIL} / demo123\n")

if __name__ == "__main__":
    main()
