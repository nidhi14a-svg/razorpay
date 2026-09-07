import sys
import os
import time
import uuid
import requests

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8000"

# Import database collections for direct verification
from database import merchants_collection, customers_collection, campaigns_collection, offers_collection

def run_test_1_unauthenticated_user():
    print("\n" + "=" * 70)
    print("TEST 1: Unauthenticated User Security Check")
    print("=" * 70)
    
    # 1. Protected endpoint without token must return 401
    res1 = requests.post(f"{BASE_URL}/customers/upload", files={"file": ("test.csv", b"id,purchase_count\n1,2", "text/csv")})
    assert res1.status_code == 401, f"Expected 401 for unauthenticated upload, got {res1.status_code}"
    print("✓ POST /customers/upload without Authorization header returns 401 Unauthorized")
    
    res2 = requests.post(f"{BASE_URL}/customers/demo")
    assert res2.status_code == 401, f"Expected 401 for unauthenticated demo, got {res2.status_code}"
    print("✓ POST /customers/demo without Authorization header returns 401 Unauthorized")
    
    res3 = requests.post(f"{BASE_URL}/customers/demo", headers={"Authorization": "Bearer invalid_fake_token"})
    assert res3.status_code == 401, f"Expected 401 for invalid token, got {res3.status_code}"
    print("✓ POST /customers/demo with invalid Bearer token returns 401 Unauthorized")
    
    print("✅ TEST 1 PASSED: Unauthenticated access is properly blocked.")


def run_test_2_new_merchant_registration_and_status():
    print("\n" + "=" * 70)
    print("TEST 2: New Merchant Registration -> Email Verification -> Onboarding State")
    print("=" * 70)
    
    test_id = uuid.uuid4().hex[:8]
    test_email = f"newbiz_{test_id}@example.com"
    test_password = "Password123!"
    test_biz = f"Acme Goods {test_id}"
    
    # 1. Register new merchant
    reg_res = requests.post(f"{BASE_URL}/auth/register", json={
        "full_name": f"Alice Founder {test_id}",
        "business_name": test_biz,
        "email": test_email,
        "password": test_password
    })
    assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
    print(f"✓ Registered new merchant: {test_email}")
    
    # 2. Check DB document for initial state
    merchant_doc = merchants_collection.find_one({"email": test_email})
    assert merchant_doc is not None, "Merchant not created in database"
    merchant_id = merchant_doc["merchant_id"]
    verification_token = merchant_doc["verification_token"]
    
    assert merchant_doc.get("onboarding_completed") is False, "onboarding_completed must start as False"
    assert merchant_doc.get("email_verified") is False, "email_verified must start as False"
    print(f"✓ DB state verified: onboarding_completed=False, email_verified=False, merchant_id={merchant_id}")
    
    # 3. Verify Email
    ver_res = requests.post(f"{BASE_URL}/auth/verify-email", json={"token": verification_token})
    assert ver_res.status_code == 200, f"Verification failed: {ver_res.text}"
    print("✓ Email verified successfully")
    
    # 4. Login as newly verified merchant
    login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    login_data = login_res.json()
    token = login_data["token"]
    
    # Onboarding completed must be False to route user to /onboarding
    assert login_data.get("onboarding_completed") is False, "Login response must indicate onboarding_completed=False"
    print("✓ Login response confirms onboarding_completed=False -> User directed to /onboarding")
    
    # 5. Check onboarding status endpoint
    status_res = requests.get(f"{BASE_URL}/merchants/{merchant_id}/onboarding-status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["onboarding_completed"] is False
    assert status_data["has_guardrails"] is False
    assert status_data["has_customers"] is False
    print(f"✓ /merchants/{merchant_id}/onboarding-status: step='{status_data['onboarding_step']}', has_guardrails=False, has_customers=False")
    
    print("✅ TEST 2 PASSED: New merchant starts with clean onboarding state.")
    return test_email, test_password, merchant_id, token


def run_test_3_guardrails_validation_and_saving(merchant_id):
    print("\n" + "=" * 70)
    print("TEST 3: Guardrail Validation and Association with Merchant")
    print("=" * 70)
    
    # 1. Update business profile
    prof_res = requests.put(f"{BASE_URL}/merchants/{merchant_id}/profile", json={
        "business_name": "Acme Handcrafted Goods",
        "business_category": "Apparel & Accessories",
        "business_description": "Curated organic apparel"
    })
    assert prof_res.status_code == 200
    print("✓ Business profile updated successfully")
    
    # 2. Test Guardrail Validation: Negative values and out-of-range discounts must fail
    invalid_rules_1 = {
        "max_discount_percentage": 150.0, # Invalid > 100
        "min_order_value": 500.0,
        "free_shipping_allowed": True
    }
    bad_res_1 = requests.put(f"{BASE_URL}/merchants/{merchant_id}/guardrails", json=invalid_rules_1)
    assert bad_res_1.status_code == 400, f"Expected 400 for discount > 100, got {bad_res_1.status_code}"
    print(f"✓ Validation correctly rejected discount > 100%: '{bad_res_1.json().get('detail')}'")
    
    invalid_rules_2 = {
        "max_discount_percentage": 15.0,
        "min_order_value": -100.0, # Invalid negative
        "free_shipping_allowed": True
    }
    bad_res_2 = requests.put(f"{BASE_URL}/merchants/{merchant_id}/guardrails", json=invalid_rules_2)
    assert bad_res_2.status_code == 400, f"Expected 400 for negative min order value, got {bad_res_2.status_code}"
    print(f"✓ Validation correctly rejected negative minimum order value: '{bad_res_2.json().get('detail')}'")
    
    # 3. Save valid merchant guardrails
    valid_rules = {
        "max_discount_percentage": 15.0,
        "min_order_value": 750.0,
        "free_shipping_allowed": True,
        "max_campaign_budget": 25000.0,
        "high_value_customer_protection": True,
        "contact_frequency_days": 7
    }
    save_res = requests.put(f"{BASE_URL}/merchants/{merchant_id}/guardrails", json=valid_rules)
    assert save_res.status_code == 200, f"Save guardrails failed: {save_res.text}"
    print("✓ Valid guardrails saved successfully")
    
    # 4. Fetch guardrails from GET endpoint
    fetch_res = requests.get(f"{BASE_URL}/merchants/{merchant_id}/guardrails")
    assert fetch_res.status_code == 200
    saved_rules = fetch_res.json().get("rules", {})
    assert saved_rules["max_discount_percentage"] == 15.0
    assert saved_rules["min_order_value"] == 750.0
    assert saved_rules["high_value_customer_protection"] is True
    print(f"✓ Retrieved guardrails match: max_discount={saved_rules['max_discount_percentage']}%, min_order={saved_rules['min_order_value']}")
    
    # 5. Check onboarding status now reflects guardrails
    status_res = requests.get(f"{BASE_URL}/merchants/{merchant_id}/onboarding-status")
    status_data = status_res.json()
    assert status_data["has_guardrails"] is True
    assert status_data["onboarding_step"] == "data_setup"
    assert status_data["onboarding_completed"] is False
    print("✓ Onboarding status advanced to 'data_setup' with has_guardrails=True")
    
    print("✅ TEST 3 PASSED: Merchant Guardrails validated and saved separately.")


def run_test_4_demo_data_flow(merchant_id, token):
    print("\n" + "=" * 70)
    print("TEST 4: Demo Data Selection -> Isolated Demo Data & Onboarding Complete")
    print("=" * 70)
    
    demo_res = requests.post(
        f"{BASE_URL}/customers/demo",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert demo_res.status_code == 200, f"Demo setup failed: {demo_res.text}"
    demo_data = demo_res.json()
    print(f"✓ Demo initialized: {demo_data['customers_count']} customers, {demo_data['segments_count']} segments")
    assert demo_data["merchant_id"] == merchant_id
    
    # Verify records in database strictly belong to this merchant
    db_customers = list(customers_collection.find({"merchant_id": merchant_id}))
    assert len(db_customers) > 0, "No customers found in database for merchant"
    for c in db_customers[:5]:
        assert c["merchant_id"] == merchant_id
        assert "segment" in c and c["segment"]
    print(f"✓ Verified {len(db_customers)} customer records isolated to merchant_id={merchant_id}")
    
    # Verify onboarding status is now completed
    status_res = requests.get(f"{BASE_URL}/merchants/{merchant_id}/onboarding-status")
    status_data = status_res.json()
    assert status_data["onboarding_completed"] is True
    print("✓ Onboarding status is now completed=True")
    
    # Verify intelligence loads
    intel_res = requests.get(f"{BASE_URL}/merchants/{merchant_id}/intelligence")
    assert intel_res.status_code == 200
    print("✓ Intelligence loads successfully for demo merchant")
    
    print("✅ TEST 4 PASSED: Demo data flow completes onboarding properly.")


def run_test_5_csv_upload_flow():
    print("\n" + "=" * 70)
    print("TEST 5: CSV Upload -> Association with Authenticated Merchant & Segmentation")
    print("=" * 70)
    
    test_id = uuid.uuid4().hex[:8]
    test_email = f"csv_{test_id}@example.com"
    test_password = "Password123!"
    
    # 1. Register & verify new CSV merchant
    requests.post(f"{BASE_URL}/auth/register", json={
        "full_name": f"Bob CSV {test_id}",
        "business_name": f"Bob CSV Store {test_id}",
        "email": test_email,
        "password": test_password
    })
    merchant_doc = merchants_collection.find_one({"email": test_email})
    merchant_id = merchant_doc["merchant_id"]
    requests.post(f"{BASE_URL}/auth/verify-email", json={"token": merchant_doc["verification_token"]})
    
    login_res = requests.post(f"{BASE_URL}/auth/login", json={"email": test_email, "password": test_password})
    token = login_res.json()["token"]
    
    # 2. Configure guardrails (10% max discount)
    custom_rules = {
        "max_discount_percentage": 10.0,
        "min_order_value": 400.0,
        "free_shipping_allowed": True,
        "max_campaign_budget": 5000.0,
        "high_value_customer_protection": True,
        "contact_frequency_days": 14
    }
    requests.put(f"{BASE_URL}/merchants/{merchant_id}/guardrails", json=custom_rules)
    print(f"✓ Guardrails configured for CSV merchant (max discount = 10%)")
    
    # 3. Upload CSV without merchant_id in CSV columns
    csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "razzz_olist_test_20.csv"))
    assert os.path.exists(csv_path), f"CSV test file not found at {csv_path}"
    
    with open(csv_path, "rb") as f:
        up_res = requests.post(
            f"{BASE_URL}/customers/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test_customers.csv", f, "text/csv")}
        )
    assert up_res.status_code == 200, f"CSV upload failed: {up_res.text}"
    up_data = up_res.json()
    print(f"✓ CSV uploaded: {up_data['rows_imported']} rows imported, {up_data['segments_calculated']} segments calculated")
    assert up_data["merchant_id"] == merchant_id
    
    # 4. Verify customers in DB are tagged with this merchant_id
    uploaded_customers = list(customers_collection.find({"merchant_id": merchant_id}))
    assert len(uploaded_customers) == up_data["rows_imported"]
    for cust in uploaded_customers:
        assert cust["merchant_id"] == merchant_id, "Customer record not tagged with authenticated merchant_id"
        assert "segment" in cust and cust["segment"], "Customer missing segment"
    print(f"✓ Verified all {len(uploaded_customers)} customers in DB belong to {merchant_id}")
    
    # 5. Check onboarding status completed
    status_res = requests.get(f"{BASE_URL}/merchants/{merchant_id}/onboarding-status")
    assert status_res.json()["onboarding_completed"] is True
    print("✓ Onboarding status is completed=True")
    
    print("✅ TEST 5 PASSED: CSV upload associates data to merchant and computes segments.")
    return merchant_id, test_email, test_password, token


def run_test_6_ai_guardrail_enforcement(merchant_id, token):
    print("\n" + "=" * 70)
    print("TEST 6: AI Campaign Generation Adheres to Merchant Guardrails as Hard Constraints")
    print("=" * 70)
    
    # Merchant has max_discount_percentage = 10.0
    camp_payload = {
        "merchant_id": merchant_id,
        "campaign_name": f"Weekend Special {uuid.uuid4().hex[:6]}",
        "campaign_description": "Boost sales for inactive users",
        "target_segment": "all"
    }
    
    camp_res = requests.post(f"{BASE_URL}/campaigns", json=camp_payload)
    assert camp_res.status_code == 200, f"Campaign creation failed: {camp_res.text}"
    camp_data = camp_res.json()
    campaign_id = camp_data["campaign_id"]
    print(f"✓ Campaign created: {campaign_id} (offers generated: {camp_data['offers_generated']})")
    
    # Retrieve all generated offers for this campaign from MongoDB
    generated_offers = list(offers_collection.find({"campaign_id": campaign_id}))
    assert len(generated_offers) > 0, "No offers were created"
    
    max_discount_observed = 0.0
    for o in generated_offers:
        disc = float(o.get("discount_percentage", 0))
        if disc > max_discount_observed:
            max_discount_observed = disc
        assert disc <= 10.0, f"CRITICAL: Offer {o['offer_id']} gave {disc}% discount, violating 10% limit!"
    
    print(f"✓ Verified all {len(generated_offers)} generated offers respect max_discount_percentage constraint (Max observed: {max_discount_observed}%)")
    print("✅ TEST 6 PASSED: AI respects merchant guardrails as hard constraints.")


def run_test_7_returning_merchant_flow(test_email, test_password, merchant_id):
    print("\n" + "=" * 70)
    print("TEST 7: Returning Merchant -> Direct to Dashboard, No Repeated Onboarding")
    print("=" * 70)
    
    # Login again
    login_res = requests.post(f"{BASE_URL}/auth/login", json={"email": test_email, "password": test_password})
    assert login_res.status_code == 200
    login_data = login_res.json()
    
    assert login_data.get("onboarding_completed") is True, "Returning merchant must have onboarding_completed=True"
    print("✓ Login response confirms onboarding_completed=True (User goes directly to /dashboard)")
    
    status_res = requests.get(f"{BASE_URL}/merchants/{merchant_id}/onboarding-status")
    status_data = status_res.json()
    assert status_data["onboarding_completed"] is True
    assert status_data["onboarding_step"] == "completed"
    print("✓ /onboarding-status confirms onboarding_step='completed'")
    
    print("✅ TEST 7 PASSED: Returning merchant is not redirected back to onboarding.")


def run_test_8_missing_guardrails_graceful_handling():
    print("\n" + "=" * 70)
    print("TEST 8: Missing Guardrails Simulation -> Graceful Error & Guidance")
    print("=" * 70)
    
    test_id = uuid.uuid4().hex[:8]
    test_email = f"noguards_{test_id}@example.com"
    test_password = "Password123!"
    
    # 1. Register & verify merchant
    requests.post(f"{BASE_URL}/auth/register", json={
        "full_name": f"NoGuards Merchant {test_id}",
        "business_name": f"NoGuards Store {test_id}",
        "email": test_email,
        "password": test_password
    })
    merchant_doc = merchants_collection.find_one({"email": test_email})
    merchant_id = merchant_doc["merchant_id"]
    requests.post(f"{BASE_URL}/auth/verify-email", json={"token": merchant_doc["verification_token"]})
    
    login_res = requests.post(f"{BASE_URL}/auth/login", json={"email": test_email, "password": test_password})
    token = login_res.json()["token"]
    
    # 2. Manually insert customers without setting rules (simulating an existing unconfigured merchant)
    customers_collection.insert_one({
        "id": f"cust_{test_id}_1",
        "merchant_id": merchant_id,
        "name": "Test Customer",
        "email": "cust@example.com",
        "purchase_count": 5,
        "lifetime_value": 1200.0,
        "days_since_last_purchase": 10,
        "average_order_value": 240.0,
        "cart_status": "none",
        "segment": "loyal"
    })
    
    # Ensure merchant rules are unset
    merchants_collection.update_one({"merchant_id": merchant_id}, {"$unset": {"rules": ""}})
    
    # 3. Check onboarding status endpoint
    status_res = requests.get(f"{BASE_URL}/merchants/{merchant_id}/onboarding-status")
    status_data = status_res.json()
    assert status_data["has_guardrails"] is False
    assert status_data["has_customers"] is True
    assert status_data["onboarding_completed"] is False
    print(f"✓ Merchant with customers but no rules has has_guardrails=False, onboarding_completed=False")
    
    # 4. Attempt to create campaign -> must return clean HTTP 400, not 500 crash
    camp_res = requests.post(f"{BASE_URL}/campaigns", json={
        "merchant_id": merchant_id,
        "campaign_name": "Test Missing Guardrails",
        "target_segment": "all"
    })
    assert camp_res.status_code == 400, f"Expected 400, got {camp_res.status_code}: {camp_res.text}"
    error_detail = camp_res.json().get("detail", "")
    assert "guardrail" in error_detail.lower() or "rules" in error_detail.lower()
    print(f"✓ Campaign generation safely returns HTTP 400 with user-facing message: '{error_detail}'")
    
    # 5. Run revenue agent -> returns clean GUARDRAILS_MISSING status, not exception
    from revenue_agent import run_revenue_agent
    agent_result = run_revenue_agent(merchant_id)
    assert agent_result["status"] == "GUARDRAILS_MISSING"
    print(f"✓ Revenue intelligence agent returns status='GUARDRAILS_MISSING' with friendly reason: '{agent_result['reason']}'")
    
    # 6. Now configure guardrails for this merchant
    save_rules_res = requests.put(f"{BASE_URL}/merchants/{merchant_id}/guardrails", json={
        "max_discount_percentage": 20.0,
        "min_order_value": 250.0,
        "free_shipping_allowed": True
    })
    assert save_rules_res.status_code == 200
    print("✓ Guardrails configured via PUT /merchants/{merchant_id}/guardrails")
    
    # 7. Now creating campaign succeeds!
    camp_res2 = requests.post(f"{BASE_URL}/campaigns", json={
        "merchant_id": merchant_id,
        "campaign_name": "Test After Configuring Guardrails",
        "target_segment": "all"
    })
    assert camp_res2.status_code == 200
    print(f"✓ After configuring guardrails, campaign creation succeeds with {camp_res2.json()['offers_generated']} offers")
    
    print("✅ TEST 8 PASSED: Missing guardrails handled gracefully and resolved via wizard.")


if __name__ == "__main__":
    print("\n" + "#" * 70)
    print("STARTING FULL ONBOARDING AND AUTHENTICATION TEST SUITE")
    print("#" * 70)
    
    try:
        # Test 1
        run_test_1_unauthenticated_user()
        
        # Test 2
        test_email, test_password, merchant_id, token = run_test_2_new_merchant_registration_and_status()
        
        # Test 3
        run_test_3_guardrails_validation_and_saving(merchant_id)
        
        # Test 4
        run_test_4_demo_data_flow(merchant_id, token)
        
        # Test 5
        csv_merchant_id, csv_email, csv_password, csv_token = run_test_5_csv_upload_flow()
        
        # Test 6
        run_test_6_ai_guardrail_enforcement(csv_merchant_id, csv_token)
        
        # Test 7
        run_test_7_returning_merchant_flow(csv_email, csv_password, csv_merchant_id)
        
        # Test 8
        run_test_8_missing_guardrails_graceful_handling()
        
        print("\n" + "=" * 70)
        print("🎉🎉🎉 ALL 8 AUDIT & ONBOARDING SCENARIOS PASSED WITH ZERO ERRORS! 🎉🎉🎉")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ TEST RUN FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
