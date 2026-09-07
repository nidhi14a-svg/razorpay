import sys
import os
import time
import uuid
import requests

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8000"

def test_scenario_1_existing_account():
    print("\n" + "=" * 60)
    print("TEST 1: Existing Demo / Account Verification")
    print("=" * 60)
    
    # 1. Login with demo@example.com
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "demo@example.com",
        "password": "demo123"
    })
    assert res.status_code == 200, f"Login failed: {res.text}"
    data = res.json()
    print(f"✓ Logged in as: {data['email']} ({data['merchant_id']})")
    assert "token" in data, "Token missing from login response"
    assert data.get("onboarding_completed") is True, f"Expected onboarding_completed True, got {data.get('onboarding_completed')}"
    print(f"✓ onboarding_completed is True for existing account: {data['onboarding_completed']}")
    
    # 2. Check onboarding status endpoint
    status_res = requests.get(f"{BASE_URL}/merchants/{data['merchant_id']}/onboarding-status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["onboarding_completed"] is True
    assert status_data["customers_count"] > 0
    print(f"✓ /merchants/{data['merchant_id']}/onboarding-status confirms completed ({status_data['customers_count']} customers)")
    
    # 3. Check customer list
    cust_res = requests.get(f"{BASE_URL}/customers?merchant_id={data['merchant_id']}")
    assert cust_res.status_code == 200
    print(f"✓ Customer list loads successfully ({len(cust_res.json().get('items', []))} customers retrieved)")
    
    # 4. Check dashboard intelligence
    intel_res = requests.get(f"{BASE_URL}/merchants/{data['merchant_id']}/intelligence")
    assert intel_res.status_code == 200
    print(f"✓ Dashboard intelligence loads successfully")
    print("✅ TEST 1 PASSED: Existing demo/account functionality verified!")


def test_scenario_2_new_merchant_demo_dataset():
    print("\n" + "=" * 60)
    print("TEST 2: New Merchant -> Email Verification -> Login -> Choose Demo Dataset")
    print("=" * 60)
    
    test_id = uuid.uuid4().hex[:8]
    test_email = f"merchant_{test_id}@example.com"
    test_password = "SecurePassword123!"
    test_biz = f"Test Store {test_id}"
    
    # 1. Register new merchant
    print(f"1. Registering new merchant: {test_email}...")
    reg_res = requests.post(f"{BASE_URL}/auth/register", json={
        "full_name": f"Owner {test_id}",
        "business_name": test_biz,
        "email": test_email,
        "password": test_password
    })
    assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
    print("✓ Registration successful")
    
    # 2. Fetch verification token directly from database to simulate clicking email link
    from database import merchants_collection, customers_collection
    merchant_doc = merchants_collection.find_one({"email": test_email})
    assert merchant_doc is not None, "Merchant not found in database"
    verification_token = merchant_doc["verification_token"]
    merchant_id = merchant_doc["merchant_id"]
    print(f"✓ Found verification token for merchant_id: {merchant_id}")
    assert merchant_doc.get("onboarding_completed") is False, "New merchant should have onboarding_completed=False"
    
    # 3. Verify email
    print("2. Verifying email...")
    ver_res = requests.post(f"{BASE_URL}/auth/verify-email", json={"token": verification_token})
    assert ver_res.status_code == 200, f"Email verification failed: {ver_res.text}"
    print("✓ Email verified successfully")
    
    # 4. Login as new merchant
    print("3. Logging in...")
    login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    login_data = login_res.json()
    token = login_data["token"]
    
    # Confirm onboarding_completed is False (directs user to /onboarding)
    assert login_data.get("onboarding_completed") is False, f"Expected onboarding_completed False, got {login_data.get('onboarding_completed')}"
    print(f"✓ onboarding_completed is False -> Merchant redirected to /onboarding")
    
    # Check onboarding status endpoint
    status_res = requests.get(f"{BASE_URL}/merchants/{merchant_id}/onboarding-status")
    assert status_res.status_code == 200
    assert status_res.json()["onboarding_completed"] is False
    print(f"✓ Status check confirms onboarding NOT completed (customers: 0)")
    
    # 5. Merchant chooses "Use Demo Dataset"
    print("4. Merchant selects 'Use Demo Dataset' on /onboarding...")
    demo_res = requests.post(f"{BASE_URL}/customers/demo", headers={
        "Authorization": f"Bearer {token}"
    })
    assert demo_res.status_code == 200, f"Demo load failed: {demo_res.text}"
    demo_data = demo_res.json()
    print(f"✓ Demo data loaded response: {demo_data}")
    assert demo_data["merchant_id"] == merchant_id, f"Expected merchant_id {merchant_id}, got {demo_data['merchant_id']}"
    assert demo_data["customers_count"] > 0, "No customers returned"
    assert demo_data["segments_count"] > 0, "No segments returned"
    
    # 6. Verify data in DB belongs to authenticated merchant
    cust_count = customers_collection.count_documents({"merchant_id": merchant_id})
    assert cust_count == demo_data["customers_count"], f"DB count {cust_count} != {demo_data['customers_count']}"
    print(f"✓ DB confirms {cust_count} customers belonging to {merchant_id}")
    
    # Verify segmentation is populated on customers
    sample_cust = customers_collection.find_one({"merchant_id": merchant_id})
    assert "segment" in sample_cust and sample_cust["segment"], "Segment not calculated"
    print(f"✓ Sample customer: {sample_cust['name']} | Segment: {sample_cust['segment']}")
    
    # Verify merchant record was preserved (not overwritten by demo_merchant_001)
    updated_merchant = merchants_collection.find_one({"merchant_id": merchant_id})
    assert updated_merchant["email"] == test_email, "Merchant email was overwritten!"
    assert updated_merchant["business_name"] == test_biz, "Merchant business name was overwritten!"
    assert updated_merchant.get("onboarding_completed") is True, "onboarding_completed is not True"
    print(f"✓ Merchant identity preserved ({updated_merchant['business_name']}), onboarding_completed set to True")
    
    # 7. Check onboarding status endpoint now returns completed
    status_res2 = requests.get(f"{BASE_URL}/merchants/{merchant_id}/onboarding-status")
    assert status_res2.status_code == 200
    assert status_res2.json()["onboarding_completed"] is True
    print(f"✓ /merchants/{merchant_id}/onboarding-status now returns completed=True")
    
    # 8. Subsequent login returns onboarding_completed: True
    login_res2 = requests.post(f"{BASE_URL}/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    assert login_res2.json()["onboarding_completed"] is True
    print(f"✓ Subsequent login immediately returns onboarding_completed=True (bypasses /onboarding)")
    
    # 9. Confirm dashboard loads
    intel_res = requests.get(f"{BASE_URL}/merchants/{merchant_id}/intelligence")
    assert intel_res.status_code == 200
    print(f"✓ Dashboard intelligence loaded successfully for {merchant_id}")
    print("✅ TEST 2 PASSED: New merchant demo dataset flow verified!")


def test_scenario_3_new_merchant_external_csv():
    print("\n" + "=" * 60)
    print("TEST 3: New Merchant -> Email Verification -> Login -> Upload External CSV")
    print("=" * 60)
    
    test_id = uuid.uuid4().hex[:8]
    test_email = f"csv_merchant_{test_id}@example.com"
    test_password = "SecurePassword123!"
    test_biz = f"CSV Store {test_id}"
    
    # 1. Register new merchant
    print(f"1. Registering new merchant: {test_email}...")
    reg_res = requests.post(f"{BASE_URL}/auth/register", json={
        "full_name": f"CSV Owner {test_id}",
        "business_name": test_biz,
        "email": test_email,
        "password": test_password
    })
    assert reg_res.status_code == 200
    
    # 2. Verify email
    from database import merchants_collection, customers_collection
    merchant_doc = merchants_collection.find_one({"email": test_email})
    verification_token = merchant_doc["verification_token"]
    merchant_id = merchant_doc["merchant_id"]
    
    requests.post(f"{BASE_URL}/auth/verify-email", json={"token": verification_token})
    print("✓ Email verified")
    
    # 3. Login
    login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    token = login_res.json()["token"]
    assert login_res.json()["onboarding_completed"] is False
    print("✓ Logged in, onboarding_completed is False")
    
    # 4. Upload external CSV (using razzz_olist_test_20.csv)
    csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "razzz_olist_test_20.csv"))
    assert os.path.exists(csv_path), f"CSV file not found at {csv_path}"
    print(f"2. Uploading CSV from: {csv_path}...")
    
    with open(csv_path, "rb") as f:
        upload_res = requests.post(
            f"{BASE_URL}/customers/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test_customers.csv", f, "text/csv")}
        )
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    upload_data = upload_res.json()
    print(f"✓ Upload response: {upload_data}")
    assert upload_data["merchant_id"] == merchant_id
    assert upload_data["rows_imported"] > 0
    assert upload_data["segments_calculated"] > 0
    
    # 5. Confirm data belongs to authenticated merchant
    db_customers = list(customers_collection.find({"merchant_id": merchant_id}))
    assert len(db_customers) == upload_data["rows_imported"]
    for c in db_customers:
        assert c["merchant_id"] == merchant_id, f"Customer {c['id']} has wrong merchant_id {c['merchant_id']}"
        assert "segment" in c and c["segment"], f"Customer {c['id']} has no segment"
    print(f"✓ Confirmed {len(db_customers)} records in DB all belong to {merchant_id} and have calculated segments")
    
    # 6. Confirm onboarding completed in DB
    updated_merchant = merchants_collection.find_one({"merchant_id": merchant_id})
    assert updated_merchant.get("onboarding_completed") is True
    print(f"✓ Merchant document updated with onboarding_completed=True")
    
    # 7. Check onboarding status endpoint
    status_res = requests.get(f"{BASE_URL}/merchants/{merchant_id}/onboarding-status")
    assert status_res.status_code == 200
    assert status_res.json()["onboarding_completed"] is True
    assert status_res.json()["customers_count"] == len(db_customers)
    print(f"✓ /merchants/{merchant_id}/onboarding-status returns completed=True ({len(db_customers)} customers)")
    
    # 8. Re-login returns onboarding_completed=True
    login_res2 = requests.post(f"{BASE_URL}/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    assert login_res2.json()["onboarding_completed"] is True
    print(f"✓ Re-login returns onboarding_completed=True (bypasses /onboarding)")
    
    # 9. Dashboard intelligence loads
    intel_res = requests.get(f"{BASE_URL}/merchants/{merchant_id}/intelligence")
    assert intel_res.status_code == 200
    print(f"✓ Dashboard intelligence loaded successfully for CSV merchant")
    print("✅ TEST 3 PASSED: New merchant CSV dataset flow verified!")


if __name__ == "__main__":
    try:
        test_scenario_1_existing_account()
        test_scenario_2_new_merchant_demo_dataset()
        test_scenario_3_new_merchant_external_csv()
        print("\n" + "*" * 60)
        print("🎉 ALL 3 ONBOARDING FLOW TEST SUITES PASSED SUCCESSFULLY!")
        print("*" * 60 + "\n")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
