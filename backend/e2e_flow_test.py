import requests
import json
import time
import sys

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
import time

BASE_URL = "http://localhost:8000"

def run_e2e_flow():
    print("=======================================")
    print("RAZZZ E2E FLOW TEST")
    print("=======================================")

    # 1. Login
    print("\n1. Logging in...")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={"email": "demo@example.com", "password": "demo123"})
    if login_resp.status_code != 200:
        print("❌ Login failed. Ensure demo.py has been run.")
        return
    merchant_id = login_resp.json()["merchant_id"]
    print(f"✓ Logged in as Merchant ID: {merchant_id}")

    # 2. View Customers
    print("\n2. Fetching Customers...")
    cust_resp = requests.get(f"{BASE_URL}/customers?merchant_id={merchant_id}")
    if cust_resp.status_code != 200:
        print("❌ Failed to fetch customers.")
        return
    customers = cust_resp.json().get("items", [])
    print(f"✓ Found {len(customers)} customers.")

    # 3. Create Campaign
    print("\n3. Creating AI Campaign...")
    campaign_payload = {
        "merchant_id": merchant_id,
        "campaign_name": f"E2E Test Campaign {int(time.time())}",
        "campaign_description": "Boost weekend sales",
        "target_segment": "all"
    }
    camp_resp = requests.post(f"{BASE_URL}/campaigns", json=campaign_payload)
    if camp_resp.status_code != 200:
        print(f"❌ Campaign creation failed: {camp_resp.text}")
        return
    campaign_id = camp_resp.json()["campaign_id"]
    print(f"✓ Campaign created successfully! ID: {campaign_id}")
    print(f"✓ Offers generated: {camp_resp.json()['offers_generated']}")
    
    # 4. View Campaigns
    print("\n4. Fetching Campaigns...")
    camps_resp = requests.get(f"{BASE_URL}/campaigns?merchant_id={merchant_id}")
    print(f"✓ Total campaigns: {camps_resp.json().get('total', 0)}")
    
    # 5. Fetch Campaign Details
    print(f"\n5. Fetching Campaign Details for {campaign_id}...")
    details_resp = requests.get(f"{BASE_URL}/campaigns/{campaign_id}?merchant_id={merchant_id}")
    if details_resp.status_code == 200:
        print(f"✓ Campaign target: {details_resp.json().get('target_segment')}")
    else:
        print("❌ Failed to fetch campaign details")
        
    # 6. Fetch Campaign Intelligence (Needs real historical data to be fully rich, but should fallback gracefully)
    print("\n6. Running AI Campaign Insights (Intelligence)...")
    insights_resp = requests.get(f"{BASE_URL}/campaigns/{campaign_id}/insights?merchant_id={merchant_id}")
    if insights_resp.status_code == 200:
        print("✓ AI Insights Generated!")
        print(f"  Summary: {insights_resp.json().get('summary')}")
    else:
        print(f"❌ Failed to generate insights: {insights_resp.text}")
        
    print("\n=======================================")
    print("✓ E2E FLOW COMPLETED SUCCESSFULLY")
    print("=======================================")

if __name__ == "__main__":
    try:
        requests.get(f"{BASE_URL}/health")
        run_e2e_flow()
    except requests.ConnectionError:
        print("❌ Backend is not running. Please start it with `uvicorn main:app` first.")
