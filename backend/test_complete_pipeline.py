import sys
import uuid
import requests
import io

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("=" * 80)
    print("STARTING E2E VERIFICATION: ONBOARDING & CSV DATA PIPELINE")
    print("=" * 80)

    # 1. AUTHENTICATION: SEPARATE REGISTER & LOGIN
    print("\n[PHASE 1] Testing Authentication & Onboarding Redirection...")
    uid = uuid.uuid4().hex[:8]
    test_email = f"pipeline_test_{uid}@example.com"
    test_pwd = "Password123!"
    test_biz = f"Pipeline Store {uid}"

    # Register
    reg_resp = requests.post(f"{BASE_URL}/auth/register", json={
        "full_name": f"Tester {uid}",
        "business_name": test_biz,
        "email": test_email,
        "password": test_pwd
    })
    assert reg_resp.status_code == 200, f"Registration failed: {reg_resp.text}"
    print(f"✓ Registered merchant: {test_email}")

    # Login immediately
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": test_email,
        "password": test_pwd
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    login_data = login_resp.json()
    assert login_data.get("onboarding_completed") is False, "New merchant must have onboarding_completed = False"
    merchant_id = login_data["merchant_id"]
    token = login_data["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"✓ Logged in as {merchant_id}. onboarding_completed={login_data['onboarding_completed']} (redirects to /onboarding)")

    # Verify dashboard protection: onboarding-status must report False
    status_resp = requests.get(f"{BASE_URL}/merchants/{merchant_id}/onboarding-status", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["onboarding_completed"] is False
    print("✓ Dashboard access protected: onboarding-status confirms is_completed=False")

    # 2. ONBOARDING STEP 1: BUSINESS INFORMATION
    print("\n[PHASE 2] Testing Step 1: Business Information...")
    prof_resp = requests.put(f"{BASE_URL}/merchants/{merchant_id}/profile", json={
        "business_name": f"Verified Brand {uid}",
        "business_category": "Home Goods",
        "business_description": "Artisan goods and decor",
        "full_name": f"Lead Founder {uid}"
    }, headers=headers)
    assert prof_resp.status_code == 200, f"Profile save failed: {prof_resp.text}"
    print("✓ Business info saved successfully.")

    # 3. ONBOARDING STEP 2: REVENUE GUARDRAILS VALIDATION
    print("\n[PHASE 3] Testing Step 2: Revenue Guardrails Validation...")
    # Both max_discount_percentage and min_margin_percentage are required and must be 0-100%
    
    # Missing min_margin_percentage -> Must fail
    bad_res1 = requests.put(f"{BASE_URL}/merchants/{merchant_id}/guardrails", json={
        "max_discount_percentage": 25.0
    }, headers=headers)
    assert bad_res1.status_code == 400, "Missing min_margin_percentage should return 400"
    print(f"✓ Missing min_margin_percentage rejected: {bad_res1.json().get('detail')}")

    # Out of range percentage (> 100) -> Must fail
    bad_res2 = requests.put(f"{BASE_URL}/merchants/{merchant_id}/guardrails", json={
        "max_discount_percentage": 120.0,
        "min_margin_percentage": 25.0
    }, headers=headers)
    assert bad_res2.status_code == 400
    print(f"✓ Out-of-bounds discount percentage rejected: {bad_res2.json().get('detail')}")

    # Negative percentage -> Must fail
    bad_res3 = requests.put(f"{BASE_URL}/merchants/{merchant_id}/guardrails", json={
        "max_discount_percentage": 20.0,
        "min_margin_percentage": -5.0
    }, headers=headers)
    assert bad_res3.status_code == 400
    print(f"✓ Negative margin percentage rejected: {bad_res3.json().get('detail')}")

    # Valid guardrails
    valid_rules = {
        "max_discount_percentage": 25.0,
        "min_margin_percentage": 30.0,
        "min_order_value": 500.0,
        "free_shipping_allowed": True
    }
    good_res = requests.put(f"{BASE_URL}/merchants/{merchant_id}/guardrails", json=valid_rules, headers=headers)
    assert good_res.status_code == 200, f"Valid guardrails failed: {good_res.text}"
    print("✓ Valid guardrails saved successfully (max_discount=25%, min_margin=30%).")

    # 4. PREVENTING EARLY ONBOARDING COMPLETION
    print("\n[PHASE 4] Testing Onboarding Completion Guard...")
    # Attempting to complete onboarding without customer data MUST FAIL
    early_complete = requests.post(f"{BASE_URL}/merchants/{merchant_id}/complete-onboarding", headers=headers)
    assert early_complete.status_code == 400, "Completing onboarding without customer data should fail"
    print(f"✓ Silent onboarding skip blocked: {early_complete.json().get('detail')}")

    # 5. STEP 3: CSV VALIDATION & PREVIEW
    print("\n[PHASE 5] Testing Step 3: CSV Validation & Preview...")
    
    # 5A: Insufficient data CSV (raw IDs without purchase/order columns) -> Must fail with explicit reason
    raw_id_csv = (
        "customer_id,city,state\n"
        "cust_1,Mumbai,MH\n"
        "cust_2,Bangalore,KA\n"
    ).encode('utf-8')
    val_bad = requests.post(
        f"{BASE_URL}/customers/validate-csv",
        files={"file": ("raw_ids.csv", raw_id_csv, "text/csv")}
    )
    assert val_bad.status_code == 400, "Raw IDs CSV without amount/order should fail validation"
    print(f"✓ Insufficient CSV columns correctly rejected: {val_bad.json().get('detail')}")

    # 5B: Valid Transactional CSV with diverse behavior
    # CUST_VIP: High LTV (3 orders, ₹3500, recent 5 days ago) -> Expected segment: VIP
    # CUST_LOYAL: Frequent purchases (3 orders, ₹600, recent 10 days ago) -> Expected segment: Loyal
    # CUST_AT_RISK: Former value (2 orders, ₹800, last order 110 days ago) -> Expected segment: At Risk
    # CUST_INACTIVE: Long ago (1 order, ₹150, last order 250 days ago) -> Expected segment: Inactive
    # CUST_REGULAR: 1 order, ₹200, 20 days ago -> Expected segment: Regular
    transactional_csv = (
        "InvoiceNo,CustomerID,UnitPrice,Quantity,InvoiceDate\n"
        "INV001,CUST_VIP,1000.00,2,2024-09-01 10:00:00\n"
        "INV002,CUST_VIP,750.00,2,2024-09-05 12:00:00\n"
        "INV003,CUST_LOYAL,100.00,2,2024-08-15 09:00:00\n"
        "INV004,CUST_LOYAL,200.00,2,2024-09-02 11:30:00\n"
        "INV005,CUST_AT_RISK,400.00,2,2024-05-15 15:00:00\n"
        "INV006,CUST_INACTIVE,150.00,1,2023-12-01 14:00:00\n"
        "INV007,CUST_REGULAR,200.00,1,2024-08-20 16:00:00\n"
    ).encode('utf-8')

    val_res = requests.post(
        f"{BASE_URL}/customers/validate-csv",
        files={"file": ("ecommerce_transactions.csv", transactional_csv, "text/csv")}
    )
    assert val_res.status_code == 200, f"CSV preview failed: {val_res.text}"
    preview_data = val_res.json()
    assert preview_data["total_unique_customers"] == 5
    assert preview_data["total_transactions"] == 7
    assert len(preview_data["preview"]) == 5
    print(f"✓ CSV Validation succeeded: {preview_data['total_unique_customers']} customers, {preview_data['total_transactions']} transactions.")
    print("  Detected Column Mappings:", preview_data["detected_column_mapping"])
    print("  Calculated Segments in Preview:", preview_data["segment_distribution"])
    for p in preview_data["preview"]:
        print(f"    - {p['customer_id']}: purchases={p['purchase_count']}, LTV=₹{p['lifetime_value']}, AOV=₹{p['average_order_value']}, days_since={p['days_since_last_purchase']}d, segment={p['segment']}")

    # Verify metrics are not 0 and segments are not all regular
    assert any(p["lifetime_value"] > 0 for p in preview_data["preview"])
    assert any(p["purchase_count"] > 0 for p in preview_data["preview"])
    assert len(preview_data["segment_distribution"]) > 1, "Segments must not all be 'regular'!"

    # 6. COMMIT IMPORT TO MONGODB (with Replace mode)
    print("\n[PHASE 6] Testing Final CSV Import & Persistence...")
    upload_res = requests.post(
        f"{BASE_URL}/customers/upload",
        data={"mode": "replace"},
        files={"file": ("ecommerce_transactions.csv", transactional_csv, "text/csv")},
        headers=headers
    )
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    upload_data = upload_res.json()
    assert upload_data["rows_imported"] == 5
    assert upload_data["onboarding_completed"] is True
    print(f"✓ Successfully imported {upload_data['rows_imported']} customers. onboarding_completed={upload_data['onboarding_completed']}")

    # 7. VERIFY CUSTOMER METRICS IN MONGODB & API
    print("\n[PHASE 7] Checking Customer List & Behavioral Metrics...")
    cust_res = requests.get(f"{BASE_URL}/customers?merchant_id={merchant_id}&page=1&limit=20")
    assert cust_res.status_code == 200
    cust_list = cust_res.json()["items"]
    assert len(cust_list) == 5
    for c in cust_list:
        assert c["purchase_count"] > 0, f"Customer {c['id']} has 0 purchase_count"
        assert c["lifetime_value"] > 0, f"Customer {c['id']} has 0 lifetime_value"
        assert c["average_order_value"] > 0, f"Customer {c['id']} has 0 AOV"
    print("✓ Verified: ALL customer records in MongoDB have calculated non-zero metrics!")

    # 8. VERIFY DASHBOARD SUMMARY API
    print("\n[PHASE 8] Testing Dashboard Summary Endpoint...")
    dash_res = requests.get(f"{BASE_URL}/merchants/{merchant_id}/dashboard-summary")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["total_customers"] == 5
    assert dash_data["total_orders"] == 7
    assert dash_data["total_revenue"] > 0
    assert dash_data["average_order_value"] > 0
    assert len(dash_data["segment_distribution"]) > 1
    print(f"✓ Dashboard Summary: Total Customers={dash_data['total_customers']}, Total Revenue=₹{dash_data['total_revenue']}, AOV=₹{dash_data['average_order_value']}, Total Orders={dash_data['total_orders']}")
    print("  Segment Distribution:", dash_data["segment_distribution"])

    # 9. VERIFY ONBOARDING COMPLETION & SUBSEQUENT LOGIN
    print("\n[PHASE 9] Verifying Subsequent Login Redirect...")
    subsequent_login = requests.post(f"{BASE_URL}/auth/login", json={
        "email": test_email,
        "password": test_pwd
    })
    assert subsequent_login.status_code == 200
    assert subsequent_login.json()["onboarding_completed"] is True, "Subsequent login must return onboarding_completed=True"
    print("✓ Subsequent login correctly returns onboarding_completed=True -> Routes to /dashboard")

    # 10. VERIFY AI INTELLIGENCE ALL 4 STATES
    print("\n[PHASE 10] Testing AI Intelligence 4 State System...")

    # State 1: MISSING_GUARDRAILS
    uid_noguard = uuid.uuid4().hex[:8]
    m_noguard = f"merch_noguard_{uid_noguard}"
    requests.post(f"{BASE_URL}/auth/register", json={
        "full_name": "No Guard", "business_name": "No Guard",
        "email": f"noguard_{uid_noguard}@example.com", "password": "Password123!"
    })
    login_noguard = requests.post(f"{BASE_URL}/auth/login", json={
        "email": f"noguard_{uid_noguard}@example.com", "password": "Password123!"
    }).json()
    res_noguard = requests.post(f"{BASE_URL}/agent/run", json={"merchant_id": login_noguard["merchant_id"]}).json()
    assert res_noguard["status"] == "MISSING_GUARDRAILS"
    print(f"✓ State 1 (MISSING_GUARDRAILS): {res_noguard['status']} - {res_noguard['reason']}")

    # Configure guardrails for this merchant, but 0 customers -> State 2: INSUFFICIENT_CUSTOMER_DATA
    requests.put(f"{BASE_URL}/merchants/{login_noguard['merchant_id']}/guardrails", json={
        "max_discount_percentage": 20.0, "min_margin_percentage": 25.0
    }, headers={"Authorization": f"Bearer {login_noguard['token']}"})
    res_nocust = requests.post(f"{BASE_URL}/agent/run", json={"merchant_id": login_noguard["merchant_id"]}).json()
    assert res_nocust["status"] == "INSUFFICIENT_CUSTOMER_DATA"
    print(f"✓ State 2 (INSUFFICIENT_CUSTOMER_DATA): {res_nocust['status']} - {res_nocust['reason']}")

    # State 3: INSUFFICIENT_BEHAVIORAL_DATA (Customers exist, but metrics are 0)
    uid_zerometrics = uuid.uuid4().hex[:8]
    requests.post(f"{BASE_URL}/auth/register", json={
        "full_name": "Zero Metrics", "business_name": "Zero Metrics",
        "email": f"zerometrics_{uid_zerometrics}@example.com", "password": "Password123!"
    })
    login_zero = requests.post(f"{BASE_URL}/auth/login", json={
        "email": f"zerometrics_{uid_zerometrics}@example.com", "password": "Password123!"
    }).json()
    m_zero_id = login_zero["merchant_id"]
    requests.put(f"{BASE_URL}/merchants/{m_zero_id}/guardrails", json={
        "max_discount_percentage": 20.0, "min_margin_percentage": 25.0
    }, headers={"Authorization": f"Bearer {login_zero['token']}"})
    
    # Insert customers with 0 metrics (simulating old faulty import)
    from database import customers_collection
    customers_collection.insert_one({
        "id": "cust_zero_1",
        "merchant_id": m_zero_id,
        "name": "Zero Metrics Customer",
        "purchase_count": 0,
        "lifetime_value": 0.0,
        "average_order_value": 0.0,
        "days_since_last_purchase": 0,
        "segment": "regular"
    })
    res_zero = requests.post(f"{BASE_URL}/agent/run", json={"merchant_id": m_zero_id}).json()
    assert res_zero["status"] == "INSUFFICIENT_BEHAVIORAL_DATA"
    assert "purchase history could not be calculated" in res_zero["reason"]
    print(f"✓ State 3 (INSUFFICIENT_BEHAVIORAL_DATA): {res_zero['status']}")
    print(f"  Detailed Reason: {res_zero['reason']}")

    # State 4: READY (Our onboarded merchant with valid guardrails & calculated metrics)
    res_ready = requests.post(f"{BASE_URL}/agent/run", json={"merchant_id": merchant_id}).json()
    assert res_ready["status"] in ["READY", "VALIDATED"]
    assert res_ready["data_sufficiency"] == "READY"
    assert res_ready["recommendation"] is not None
    print(f"✓ State 4 (READY): Strategy generated: '{res_ready.get('strategy')}'")
    print(f"  Recommended Offer: {res_ready['recommendation'].get('offer')} ({res_ready['recommendation'].get('discount_percentage')}% discount for segment '{res_ready['recommendation'].get('segment')}')")
    print(f"  Guardrail Validation: {res_ready['guardrail_result']['status']} ({res_ready['guardrail_result']['reason']})")

    print("\n" + "=" * 80)
    print("ALL 10 PIPELINE PHASES VERIFIED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
