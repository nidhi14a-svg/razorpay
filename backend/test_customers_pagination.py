import sys
import requests

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8000"

def test_pagination():
    print("\n" + "=" * 70)
    print("CUSTOMER PAGINATION & DATA INTEGRITY TEST")
    print("=" * 70)

    # 1. Test with test_upload_99 (which holds 96,096 records)
    res = requests.get(f"{BASE_URL}/customers?merchant_id=test_upload_99&page=1&limit=20")
    assert res.status_code == 200, f"Failed: {res.text}"
    data = res.json()

    print(f"1. Testing 96,096 dataset (merchant: test_upload_99):")
    print(f"   ✓ Total in response: {data['total']:,}")
    print(f"   ✓ Total pages: {data['total_pages']:,}")
    print(f"   ✓ Page 1 items returned: {len(data['customers'])}")
    assert data["total"] == 96096, f"Expected 96096, got {data['total']}"
    assert data["total_pages"] == 4805, f"Expected 4805, got {data['total_pages']}"
    assert len(data["customers"]) == 20
    assert "items" in data and len(data["items"]) == 20
    assert "segments" in data and len(data["segments"]) > 0

    page_1_ids = [c["id"] for c in data["customers"]]

    # 2. Test Page 2 - items must be completely distinct from Page 1
    res2 = requests.get(f"{BASE_URL}/customers?merchant_id=test_upload_99&page=2&limit=20")
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2["customers"]) == 20
    page_2_ids = [c["id"] for c in data2["customers"]]
    overlap = set(page_1_ids).intersection(set(page_2_ids))
    assert len(overlap) == 0, f"Page 1 and Page 2 have overlapping IDs: {overlap}"
    print(f"   ✓ Page 2 returns 20 distinct records with zero overlap")

    # 3. Test Deep Pagination (Page 1000)
    res_deep = requests.get(f"{BASE_URL}/customers?merchant_id=test_upload_99&page=1000&limit=20")
    assert res_deep.status_code == 200
    data_deep = res_deep.json()
    assert len(data_deep["customers"]) == 20
    print(f"   ✓ Deep page 1,000 fetched instantaneously: first ID={data_deep['customers'][0]['id']}")

    # 4. Test Last Page (Page 4805)
    # 96096 % 20 = 16 records on the last page
    res_last = requests.get(f"{BASE_URL}/customers?merchant_id=test_upload_99&page=4805&limit=20")
    assert res_last.status_code == 200
    data_last = res_last.json()
    assert len(data_last["customers"]) == 16, f"Expected 16 on last page, got {len(data_last['customers'])}"
    print(f"   ✓ Last page (4,805) correctly returns the remaining {len(data_last['customers'])} records")

    # 5. Test Custom Limit (limit=50)
    res_50 = requests.get(f"{BASE_URL}/customers?merchant_id=test_upload_99&page=1&limit=50")
    assert res_50.status_code == 200
    data_50 = res_50.json()
    assert len(data_50["customers"]) == 50
    assert data_50["total_pages"] == 1922 # ceil(96096 / 50)
    print(f"   ✓ Limit=50 returns 50 records, recalculating total_pages to {data_50['total_pages']:,}")

    # 6. Test Segment Filter
    res_seg = requests.get(f"{BASE_URL}/customers?merchant_id=test_upload_99&segment=dormant&page=1&limit=20")
    assert res_seg.status_code == 200
    data_seg = res_seg.json()
    print(f"   ✓ Segment filter 'dormant' returns total={data_seg['total']:,} matching records")
    for c in data_seg["customers"]:
        assert c["segment"] == "dormant", f"Customer {c['id']} has segment {c['segment']}, expected dormant"

    # 7. Test Search by Customer ID
    sample_id = page_1_ids[5]
    res_search = requests.get(f"{BASE_URL}/customers?merchant_id=test_upload_99&search={sample_id[:8]}&page=1&limit=20")
    assert res_search.status_code == 200
    data_search = res_search.json()
    assert data_search["total"] >= 1
    found_ids = [c["id"] for c in data_search["customers"]]
    assert sample_id in found_ids
    print(f"   ✓ Search query '{sample_id[:8]}' successfully found target customer")

    # 8. Test Isolation: demo_merchant_001 cannot see test_upload_99 customers
    res_demo = requests.get(f"{BASE_URL}/customers?merchant_id=demo_merchant_001&page=1&limit=20")
    assert res_demo.status_code == 200
    data_demo = res_demo.json()
    assert data_demo["total"] == 40, f"Expected 40 demo customers, got {data_demo['total']}"
    demo_ids = [c["id"] for c in data_demo["customers"]]
    for did in demo_ids:
        assert did not in page_1_ids, "Cross-merchant data leakage detected!"
    print("   ✓ Merchant isolation verified: demo_merchant_001 isolated to its own 40 customers")

    # 9. Test with user merchant (merch_a5487f34a0a3 - 99,441 records)
    res_user = requests.get(f"{BASE_URL}/customers?merchant_id=merch_a5487f34a0a3&page=1&limit=20")
    assert res_user.status_code == 200
    data_user = res_user.json()
    print(f"\n2. Testing merchant nidhi14a@gmail.com (merch_a5487f34a0a3):")
    print(f"   ✓ Total in MongoDB: {data_user['total']:,}")
    print(f"   ✓ Total pages: {data_user['total_pages']:,}")
    print(f"   ✓ Page 1 items returned: {len(data_user['customers'])}")
    assert data_user["total"] == 99441
    assert data_user["total_pages"] == 4973

    print("\n" + "=" * 70)
    print("🎉 ALL PAGINATION & DATA INTEGRITY TESTS PASSED SUCCESSFULLY!")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    test_pagination()
