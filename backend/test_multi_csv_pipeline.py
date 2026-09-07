import sys
import uuid
import requests

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

def test_multi_csv_pipeline():
    print("=" * 80)
    print("TESTING MULTI-CSV RELATIONAL DATA PIPELINE & AI INTELLIGENCE")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # 1. PREPARE RELATIONAL TEST DATASETS (Olist Schema)
    # -------------------------------------------------------------------------
    print("\n[STEP 1] Generating Synthetic Olist-Style Relational Datasets...")

    customers_csv = (
        "customer_id,customer_unique_id,customer_zip_code_prefix,customer_city,customer_state\n"
        "CUST_VIP_1,UNIQ_001,40001,Mumbai,MH\n"
        "CUST_LOYAL_2,UNIQ_002,56001,Bangalore,KA\n"
        "CUST_AT_RISK_3,UNIQ_003,11001,Delhi,DL\n"
        "CUST_INACTIVE_4,UNIQ_004,60001,Chennai,TN\n"
        "CUST_NO_ORDERS_5,UNIQ_005,50001,Hyderabad,TS\n"
    ).encode('utf-8')

    orders_csv = (
        "order_id,customer_id,order_status,order_purchase_timestamp\n"
        "ORD_101,CUST_VIP_1,delivered,2024-09-01 10:00:00\n"
        "ORD_102,CUST_VIP_1,delivered,2024-09-05 12:00:00\n"
        "ORD_103,CUST_LOYAL_2,delivered,2024-08-15 09:00:00\n"
        "ORD_104,CUST_LOYAL_2,delivered,2024-09-02 11:30:00\n"
        "ORD_105,CUST_AT_RISK_3,delivered,2024-05-15 15:00:00\n"
        "ORD_106,CUST_INACTIVE_4,delivered,2023-12-01 14:00:00\n"
    ).encode('utf-8')

    order_items_csv = (
        "order_id,order_item_id,product_id,price,freight_value\n"
        "ORD_101,1,PROD_A,1200.00,50.00\n"
        "ORD_101,2,PROD_B,300.00,20.00\n"
        "ORD_102,1,PROD_C,800.00,30.00\n"
        "ORD_103,1,PROD_D,150.00,15.00\n"
        "ORD_104,1,PROD_E,250.00,20.00\n"
        "ORD_105,1,PROD_F,400.00,25.00\n"
        "ORD_106,1,PROD_G,120.00,10.00\n"
    ).encode('utf-8')

    print("✓ Created: customers_csv (5 rows), orders_csv (6 orders), order_items_csv (7 items)")

    # -------------------------------------------------------------------------
    # 2. TEST VALIDATION & PREVIEW (POST /customers/validate-multi-csv)
    # -------------------------------------------------------------------------
    print("\n[STEP 2] Testing Validation & Preview Endpoint...")
    val_resp = requests.post(
        f"{BASE_URL}/customers/validate-multi-csv",
        files={
            "customers_file": ("olist_customers_dataset.csv", customers_csv, "text/csv"),
            "orders_file": ("olist_orders_dataset.csv", orders_csv, "text/csv"),
            "order_items_file": ("olist_order_items_dataset.csv", order_items_csv, "text/csv")
        }
    )
    assert val_resp.status_code == 200, f"Validation failed: {val_resp.text}"
    preview_data = val_resp.json()

    print(f"✓ Validation Succeeded!")
    print(f"  Total Customer Rows: {preview_data['total_customer_rows']}")
    print(f"  Total Unique Customers: {preview_data['total_unique_customers']}")
    print(f"  Total Orders: {preview_data['total_orders']}")
    print(f"  Total Order Items: {preview_data['total_order_items']}")
    print(f"  Matched Customers: {preview_data['matched_customers_count']}")
    print(f"  Unmatched Customers (no orders): {preview_data['unmatched_customers_count']}")
    print(f"  Detected Mappings: {preview_data['detected_column_mappings']}")
    print(f"  Segment Distribution: {preview_data['segment_distribution']}")

    assert preview_data["total_customer_rows"] == 5
    assert preview_data["total_orders"] == 6
    assert preview_data["total_order_items"] == 7
    assert preview_data["matched_customers_count"] == 4
    assert preview_data["unmatched_customers_count"] == 1

    # Check that top preview records have calculated metrics
    p0 = preview_data["preview"][0]
    print(f"  Top Preview Customer: {p0['customer_id']} -> purchases={p0['purchase_count']}, LTV=₹{p0['lifetime_value']}, AOV=₹{p0['average_order_value']}, segment={p0['segment']}")
    assert p0["lifetime_value"] > 0
    assert p0["purchase_count"] > 0
    assert p0["average_order_value"] > 0

    # -------------------------------------------------------------------------
    # 3. TEST CLEAR ERROR HANDLING ON MISSING JOIN COLUMN
    # -------------------------------------------------------------------------
    print("\n[STEP 3] Testing Clear Error Reporting on Missing Join Columns...")
    bad_orders_csv = (
        "order_id,order_status,order_purchase_timestamp\n"
        "ORD_101,delivered,2024-09-01 10:00:00\n"
    ).encode('utf-8')

    bad_val = requests.post(
        f"{BASE_URL}/customers/validate-multi-csv",
        files={
            "customers_file": ("customers.csv", customers_csv, "text/csv"),
            "orders_file": ("bad_orders.csv", bad_orders_csv, "text/csv"),
            "order_items_file": ("order_items.csv", order_items_csv, "text/csv")
        }
    )
    assert bad_val.status_code == 400
    err_detail = bad_val.json().get("detail", "")
    print(f"✓ Correctly rejected missing customer_id: {err_detail}")
    assert "customer_id" in err_detail.lower()

    # -------------------------------------------------------------------------
    # 4. REGISTER & CONFIGURE MERCHANT, THEN TEST MULTI-CSV UPLOAD
    # -------------------------------------------------------------------------
    print("\n[STEP 4] Registering New Merchant & Uploading Relational Dataset...")
    uid = uuid.uuid4().hex[:8]
    test_email = f"multi_test_{uid}@example.com"
    test_pwd = "Password123!"

    reg = requests.post(f"{BASE_URL}/auth/register", json={
        "full_name": f"Multi Tester {uid}",
        "business_name": f"Multi Store {uid}",
        "email": test_email,
        "password": test_pwd
    }).json()

    login = requests.post(f"{BASE_URL}/auth/login", json={
        "email": test_email,
        "password": test_pwd
    }).json()
    merchant_id = login["merchant_id"]
    token = login["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Business info
    requests.put(f"{BASE_URL}/merchants/{merchant_id}/profile", json={
        "business_name": f"Multi Store {uid}",
        "business_category": "E-commerce"
    }, headers=headers)

    # Step 2: Guardrails
    requests.put(f"{BASE_URL}/merchants/{merchant_id}/guardrails", json={
        "max_discount_percentage": 25.0,
        "min_margin_percentage": 30.0
    }, headers=headers)

    # Step 3: Multi-CSV Upload
    upload_resp = requests.post(
        f"{BASE_URL}/customers/upload-multi",
        data={"mode": "replace"},
        files={
            "customers_file": ("olist_customers_dataset.csv", customers_csv, "text/csv"),
            "orders_file": ("olist_orders_dataset.csv", orders_csv, "text/csv"),
            "order_items_file": ("olist_order_items_dataset.csv", order_items_csv, "text/csv")
        },
        headers=headers
    )
    assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
    upload_data = upload_resp.json()
    print(f"✓ Upload succeeded!")
    print(f"  Rows Imported: {upload_data['rows_imported']}")
    print(f"  Matched Customers: {upload_data['matched_customers']}")
    print(f"  Unmatched Customers: {upload_data['unmatched_customers']}")
    print(f"  Segments: {upload_data['segments_calculated']}")
    print(f"  Onboarding Completed: {upload_data['onboarding_completed']}")

    assert upload_data["rows_imported"] == 5
    assert upload_data["matched_customers"] == 4
    assert upload_data["unmatched_customers"] == 1
    assert upload_data["onboarding_completed"] is True

    # -------------------------------------------------------------------------
    # 5. VERIFY DATABASE PERSISTENCE & METRIC CORRECTNESS
    # -------------------------------------------------------------------------
    print("\n[STEP 5] Checking MongoDB Customer Records...")
    from database import customers_collection
    stored_customers = list(customers_collection.find({"merchant_id": merchant_id}))
    assert len(stored_customers) == 5

    cust_map = {c["id"]: c for c in stored_customers}
    vip1 = cust_map["CUST_VIP_1"]
    print(f"  CUST_VIP_1: purchases={vip1['purchase_count']}, LTV=₹{vip1['lifetime_value']}, AOV=₹{vip1['average_order_value']}, segment={vip1['segment']}")
    assert vip1["purchase_count"] == 2
    assert vip1["lifetime_value"] == 2300.0  # (1200+300) + 800
    assert vip1["average_order_value"] == 1150.0

    no_order_cust = cust_map["CUST_NO_ORDERS_5"]
    print(f"  CUST_NO_ORDERS_5: purchases={no_order_cust['purchase_count']}, LTV=₹{no_order_cust['lifetime_value']}, segment={no_order_cust['segment']}, has_orders={no_order_cust['has_orders']}")
    assert no_order_cust["purchase_count"] == 0
    assert no_order_cust["lifetime_value"] == 0.0
    assert no_order_cust["has_orders"] is False
    assert no_order_cust["segment"] == "inactive"

    print("✓ Database records verified: Valid non-zero metrics for buyers, clean zero/inactive for non-buyers!")

    # -------------------------------------------------------------------------
    # 6. VERIFY AI INTELLIGENCE IS 'READY' FOR THIS MERCHANT
    # -------------------------------------------------------------------------
    print("\n[STEP 6] Testing AI Intelligence Engine on Multi-CSV Merchant...")
    agent_resp = requests.post(f"{BASE_URL}/agent/run", json={"merchant_id": merchant_id}).json()
    print(f"✓ AI Intelligence Status: {agent_resp['status']}")
    print(f"  Strategy: '{agent_resp.get('strategy')}'")
    print(f"  Recommendation: {agent_resp.get('recommendation')}")
    print(f"  Guardrail Validation: {agent_resp.get('guardrail_result')}")
    assert agent_resp["status"] in ["READY", "VALIDATED"]
    assert agent_resp["data_sufficiency"] == "READY"
    assert agent_resp["recommendation"] is not None

    # -------------------------------------------------------------------------
    # 7. VERIFY AI INTELLIGENCE EXPLICIT STATUSES: NO_CUSTOMER_DATA & INSUFFICIENT_BEHAVIORAL_DATA
    # -------------------------------------------------------------------------
    print("\n[STEP 7] Testing AI Intelligence Incomplete Data States...")
    # Register empty merchant with guardrails
    requests.post(f"{BASE_URL}/auth/register", json={
        "full_name": "Empty Merchant", "business_name": "Empty Store",
        "email": f"empty_{uid}@example.com", "password": "Password123!"
    })
    login_empty_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": f"empty_{uid}@example.com", "password": "Password123!"
    }).json()
    m_empty = login_empty_resp["merchant_id"]
    tok_empty = login_empty_resp["token"]
    
    # Configure guardrails
    requests.put(f"{BASE_URL}/merchants/{m_empty}/guardrails", json={
        "max_discount_percentage": 20.0, "min_margin_percentage": 25.0
    }, headers={"Authorization": f"Bearer {tok_empty}"})

    res_no_cust = requests.post(f"{BASE_URL}/agent/run", json={"merchant_id": m_empty}).json()
    assert res_no_cust["status"] == "NO_CUSTOMER_DATA"
    print(f"✓ Verified State NO_CUSTOMER_DATA: {res_no_cust['status']} - {res_no_cust['reason']}")

    # Now insert customer with only demographic data (all metrics 0)
    customers_collection.insert_one({
        "id": f"demographic_only_{uid}",
        "merchant_id": m_empty,
        "name": "Demographic Customer",
        "purchase_count": 0,
        "lifetime_value": 0.0,
        "average_order_value": 0.0,
        "days_since_last_purchase": 0,
        "segment": "regular"
    })
    res_behav = requests.post(f"{BASE_URL}/agent/run", json={"merchant_id": m_empty}).json()
    assert res_behav["status"] == "INSUFFICIENT_BEHAVIORAL_DATA"
    print(f"✓ Verified State INSUFFICIENT_BEHAVIORAL_DATA: {res_behav['status']}")
    print(f"  Explanation: {res_behav['reason']}")
    assert "demographic data only" in res_behav["reason"].lower()

    print("\n" + "=" * 80)
    print("ALL MULTI-CSV BACKEND TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 80)

if __name__ == "__main__":
    test_multi_csv_pipeline()
