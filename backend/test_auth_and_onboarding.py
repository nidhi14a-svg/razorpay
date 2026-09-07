import sys
import uuid
import requests

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8000"

from database import merchants_collection, customers_collection

def test_full_auth_and_onboarding():
    print("=" * 70)
    print("RUNNING COMPREHENSIVE AUTH & ONBOARDING FLOW VERIFICATION")
    print("=" * 70)

    # -------------------------------------------------------------
    # 0. Check Real Merchant Protection First
    # -------------------------------------------------------------
    real_merchant = merchants_collection.find_one({"merchant_id": "merch_a5487f34a0a3"})
    if real_merchant:
        real_cust_count = customers_collection.count_documents({"merchant_id": "merch_a5487f34a0a3"})
        print(f"✓ Real merchant merch_a5487f34a0a3 intact: {real_cust_count} customer records")
        assert real_cust_count > 90000, f"Real merchant records unexpectedly modified: {real_cust_count}"

    # -------------------------------------------------------------
    # 1. PROBLEM 1: EMAIL VERIFICATION BYPASS FOR LOCAL TESTING
    # -------------------------------------------------------------
    print("\n--- TEST 1: Registration and Dev Login Bypass ---")
    uid = uuid.uuid4().hex[:8]
    test_email = f"dev_merchant_{uid}@example.com"
    test_password = "Password123!"
    test_name = f"Dev Merchant {uid}"
    test_biz = f"Acme Store {uid}"

    reg_res = requests.post(f"{BASE_URL}/auth/register", json={
        "full_name": test_name,
        "business_name": test_biz,
        "email": test_email,
        "password": test_password
    })
    assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
    reg_data = reg_res.json()
    assert "require_email_verification" in reg_data, "require_email_verification flag missing in register response"
    assert reg_data["require_email_verification"] is False, "Expected require_email_verification=False in dev mode"
    print(f"✓ Registered new merchant {test_email} with dev bypass message: '{reg_data['message']}'")

    # Verify DB state: email_verified must still be False in DB (preserving schema and logic!)
    merchant_doc = merchants_collection.find_one({"email": test_email})
    assert merchant_doc is not None
    assert merchant_doc.get("email_verified") is False, "email_verified in DB must remain False"
    merchant_id = merchant_doc["merchant_id"]
    print(f"✓ Preserved DB schema: email_verified=False for merchant {merchant_id}")

    # Login immediately WITHOUT verifying email
    login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    assert login_res.status_code == 200, f"Login failed for unverified user: {login_res.text}"
    login_data = login_res.json()
    assert login_data.get("merchant_id") == merchant_id
    assert login_data.get("onboarding_completed") is False, "onboarding_completed must start as False"
    assert "token" in login_data and login_data["token"], "Session token missing"
    token = login_data["token"]
    print(f"✓ Successfully logged in without email verification. onboarding_completed=False, token issued.")

    # -------------------------------------------------------------
    # 2. STEP 1: BUSINESS INFORMATION
    # -------------------------------------------------------------
    print("\n--- TEST 2: Step 1 - Business Information ---")
    status_res = requests.get(f"{BASE_URL}/merchants/{merchant_id}/onboarding-status", headers={"Authorization": f"Bearer {token}"})
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["onboarding_step"] == "business_setup"
    assert status_data["merchant_id"] == merchant_id
    assert status_data["onboarding_completed"] is False
    print(f"✓ Onboarding status correctly starts at step='business_setup'")

    # Update/confirm business profile with merchant's own account
    updated_name = f"Alice Founder {uid}"
    updated_biz = f"Acme Handcrafted Goods {uid}"
    prof_res = requests.put(f"{BASE_URL}/merchants/{merchant_id}/profile", json={
        "full_name": updated_name,
        "business_name": updated_biz,
        "business_category": "Apparel & Fashion",
        "business_description": "Handcrafted organic apparel"
    }, headers={"Authorization": f"Bearer {token}"})
    assert prof_res.status_code == 200, f"Failed to update profile: {prof_res.text}"

    # Verify profile persisted in DB
    updated_doc = merchants_collection.find_one({"merchant_id": merchant_id})
    assert updated_doc["full_name"] == updated_name
    assert updated_doc["business_name"] == updated_biz
    print(f"✓ Step 1 saved: full_name='{updated_name}', business_name='{updated_biz}'")

    # -------------------------------------------------------------
    # 3. STEP 2: GUARDRAIL RULES
    # -------------------------------------------------------------
    print("\n--- TEST 3: Step 2 - Guardrail Rules ---")
    # Validation test: discount > 100 must fail
    invalid_res = requests.put(f"{BASE_URL}/merchants/{merchant_id}/guardrails", json={
        "max_discount_percentage": 110.0,
        "min_margin_percentage": 25.0
    }, headers={"Authorization": f"Bearer {token}"})
    assert invalid_res.status_code == 400
    print("✓ Guardrail validation: discount > 100% correctly rejected with HTTP 400")

    # Save valid merchant guardrails
    valid_rules = {
        "max_discount_percentage": 25.0,
        "min_margin_percentage": 30.0,
        "min_order_value": 750.0,
        "free_shipping_allowed": True,
        "max_campaign_budget": 35000.0,
        "high_value_customer_protection": True,
        "contact_frequency_days": 7
    }
    save_res = requests.put(f"{BASE_URL}/merchants/{merchant_id}/guardrails", json=valid_rules, headers={"Authorization": f"Bearer {token}"})
    assert save_res.status_code == 200, f"Failed to save guardrails: {save_res.text}"

    # Verify guardrails stored specifically for this merchant
    db_merchant = merchants_collection.find_one({"merchant_id": merchant_id})
    saved_rules = db_merchant.get("rules", {})
    assert saved_rules["max_discount_percentage"] == 25.0
    assert saved_rules["min_margin_percentage"] == 30.0
    print(f"✓ Step 2 saved: max_discount={saved_rules['max_discount_percentage']}%, min_margin={saved_rules['min_margin_percentage']}%")

    # Check status moved to data_setup
    status_res = requests.get(f"{BASE_URL}/merchants/{merchant_id}/onboarding-status", headers={"Authorization": f"Bearer {token}"})
    status_data = status_res.json()
    assert status_data["has_guardrails"] is True
    assert status_data["onboarding_step"] == "data_setup"
    assert status_data["onboarding_completed"] is False
    print("✓ Status progressed to 'data_setup' with has_guardrails=True")

    # -------------------------------------------------------------
    # 4. STEP 3: CUSTOMER DATA UPLOAD & ONBOARDING COMPLETION
    # -------------------------------------------------------------
    print("\n--- TEST 4A: Step 3 - Skip Option Completes Onboarding ---")
    # Complete onboarding via skip
    skip_res = requests.post(f"{BASE_URL}/merchants/{merchant_id}/complete-onboarding", headers={"Authorization": f"Bearer {token}"})
    assert skip_res.status_code == 200, f"Failed to complete onboarding: {skip_res.text}"
    assert skip_res.json()["onboarding_completed"] is True

    # Verify status in DB and status endpoint
    status_res = requests.get(f"{BASE_URL}/merchants/{merchant_id}/onboarding-status", headers={"Authorization": f"Bearer {token}"})
    assert status_res.json()["onboarding_completed"] is True
    print("✓ Status now confirms onboarding_completed=True")

    # Verify subsequent login returns onboarding_completed=True -> Routes to /dashboard
    login_again = requests.post(f"{BASE_URL}/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    assert login_again.status_code == 200
    assert login_again.json()["onboarding_completed"] is True
    print("✓ Subsequent login returns onboarding_completed=True -> User directed to /dashboard")

    # -------------------------------------------------------------
    # 5. STEP 3 ALTERNATIVES: DEMO DATASET & CSV UPLOAD
    # -------------------------------------------------------------
    print("\n--- TEST 4B: Step 3 - Demo Dataset Alternative ---")
    uid2 = uuid.uuid4().hex[:8]
    test_email2 = f"dev_demo_{uid2}@example.com"
    requests.post(f"{BASE_URL}/auth/register", json={
        "full_name": f"Demo Merchant {uid2}",
        "business_name": f"Demo Store {uid2}",
        "email": test_email2,
        "password": test_password
    })
    login_data2 = requests.post(f"{BASE_URL}/auth/login", json={"email": test_email2, "password": test_password}).json()
    m2_id = login_data2["merchant_id"]
    m2_token = login_data2["token"]

    # Step 1 & 2
    requests.put(f"{BASE_URL}/merchants/{m2_id}/profile", json={"full_name": f"Demo {uid2}", "business_name": f"Demo {uid2}"}, headers={"Authorization": f"Bearer {m2_token}"})
    requests.put(f"{BASE_URL}/merchants/{m2_id}/guardrails", json={"max_discount_percentage": 20.0, "min_margin_percentage": 25.0}, headers={"Authorization": f"Bearer {m2_token}"})

    # Step 3: Load Demo
    demo_res = requests.post(f"{BASE_URL}/customers/demo", headers={"Authorization": f"Bearer {m2_token}"})
    assert demo_res.status_code == 200
    assert demo_res.json()["merchant_id"] == m2_id
    assert demo_res.json()["onboarding_completed"] is True

    # Verify customers strictly belong to m2_id
    m2_customers = list(customers_collection.find({"merchant_id": m2_id}))
    assert len(m2_customers) > 0
    for c in m2_customers[:5]:
        assert c["merchant_id"] == m2_id
    print(f"✓ Demo dataset isolated to {m2_id}: {len(m2_customers)} customers loaded and onboarding completed")

    print("\n--- TEST 4C: Step 3 - CSV Upload Alternative ---")
    uid3 = uuid.uuid4().hex[:8]
    test_email3 = f"dev_csv_{uid3}@example.com"
    requests.post(f"{BASE_URL}/auth/register", json={
        "full_name": f"CSV Merchant {uid3}",
        "business_name": f"CSV Store {uid3}",
        "email": test_email3,
        "password": test_password
    })
    login_data3 = requests.post(f"{BASE_URL}/auth/login", json={"email": test_email3, "password": test_password}).json()
    m3_id = login_data3["merchant_id"]
    m3_token = login_data3["token"]

    # Step 1 & 2
    requests.put(f"{BASE_URL}/merchants/{m3_id}/profile", json={"full_name": f"CSV {uid3}", "business_name": f"CSV {uid3}"}, headers={"Authorization": f"Bearer {m3_token}"})
    requests.put(f"{BASE_URL}/merchants/{m3_id}/guardrails", json={"max_discount_percentage": 20.0, "min_margin_percentage": 25.0}, headers={"Authorization": f"Bearer {m3_token}"})

    # Step 3: Upload CSV
    csv_content = (
        "id,name,email,purchase_count,lifetime_value,days_since_last_purchase,average_order_value\n"
        f"cust_{uid3}_1,John Doe,john@test.com,5,1250.0,14,250.0\n"
        f"cust_{uid3}_2,Jane Smith,jane@test.com,1,300.0,65,300.0\n"
    )
    upload_res = requests.post(
        f"{BASE_URL}/customers/upload",
        files={"file": ("customers.csv", csv_content.encode("utf-8"), "text/csv")},
        headers={"Authorization": f"Bearer {m3_token}"}
    )
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    assert upload_res.json()["rows_imported"] == 2
    assert upload_res.json()["merchant_id"] == m3_id

    # Verify records in DB
    m3_customers = list(customers_collection.find({"merchant_id": m3_id}))
    assert len(m3_customers) == 2
    for c in m3_customers:
        assert c["merchant_id"] == m3_id
    print(f"✓ CSV upload strictly isolated to {m3_id}: {len(m3_customers)} records imported")

    # -------------------------------------------------------------
    # 6. Final Real Account Protection Check
    # -------------------------------------------------------------
    if real_merchant:
        final_real_cust_count = customers_collection.count_documents({"merchant_id": "merch_a5487f34a0a3"})
        assert final_real_cust_count == real_cust_count, f"Real merchant records changed! Was {real_cust_count}, now {final_real_cust_count}"
        print(f"✓ Verified real merchant merch_a5487f34a0a3 remains 100% untouched ({final_real_cust_count} records)")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY! AUTH & ONBOARDING FULLY VERIFIED.")
    print("=" * 70)

if __name__ == "__main__":
    test_full_auth_and_onboarding()
