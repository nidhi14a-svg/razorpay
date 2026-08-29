import pytest
from fastapi.testclient import TestClient
import uuid

from main import app
from database import optimizations_collection, optimization_executions_collection, merchants_collection, offers_collection, campaigns_collection

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    merchants_collection.delete_many({"merchant_id": {"$regex": "^test_exec_"}})
    campaigns_collection.delete_many({"merchant_id": {"$regex": "^test_exec_"}})
    offers_collection.delete_many({"merchant_id": {"$regex": "^test_exec_"}})
    optimizations_collection.delete_many({"merchant_id": {"$regex": "^test_exec_"}})
    optimization_executions_collection.delete_many({"merchant_id": {"$regex": "^test_exec_"}})
    
    merchants_collection.insert_one({
        "merchant_id": "test_exec_merchant",
        "rules": {
            "max_discount_percentage": 20.0,
            "min_margin_percentage": 30.0
        }
    })
    
    yield
    
    merchants_collection.delete_many({"merchant_id": {"$regex": "^test_exec_"}})
    campaigns_collection.delete_many({"merchant_id": {"$regex": "^test_exec_"}})
    offers_collection.delete_many({"merchant_id": {"$regex": "^test_exec_"}})
    optimizations_collection.delete_many({"merchant_id": {"$regex": "^test_exec_"}})
    optimization_executions_collection.delete_many({"merchant_id": {"$regex": "^test_exec_"}})


def setup_optimization(status="GENERATED", recs=None):
    opt_id = f"opt_{uuid.uuid4()}"
    camp_id = f"camp_{uuid.uuid4()}"
    
    if recs is None:
        recs = [{
            "type": "discount_adjustment",
            "segment": "new_visitor",
            "recommended_change": "Increase discount to 15%",
            "reason": "Test",
            "priority": "high",
            "status": "GENERATED"
        }]
        
    optimizations_collection.insert_one({
        "optimization_id": opt_id,
        "campaign_id": camp_id,
        "merchant_id": "test_exec_merchant",
        "status": status,
        "recommendations": recs
    })
    
    offers_collection.insert_one({
        "offer_id": f"offer_{uuid.uuid4()}",
        "merchant_id": "test_exec_merchant",
        "campaign_id": camp_id,
        "customer_segment": "new_visitor",
        "discount_percentage": 10.0,
        "status": "OFFER_CREATED"
    })
    
    return opt_id


def test_1_approve_generated():
    opt_id = setup_optimization(status="GENERATED")
    response = client.post(f"/optimizations/{opt_id}/approve?merchant_id=test_exec_merchant")
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"
    
def test_2_reject_generated():
    opt_id = setup_optimization(status="GENERATED")
    response = client.post(f"/optimizations/{opt_id}/reject?merchant_id=test_exec_merchant", json={"reason": "Not now"})
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    assert response.json()["rejection_reason"] == "Not now"

def test_3_cannot_approve_rejected():
    opt_id = setup_optimization(status="REJECTED")
    response = client.post(f"/optimizations/{opt_id}/approve?merchant_id=test_exec_merchant")
    assert response.status_code == 400

def test_4_cannot_approve_approved():
    opt_id = setup_optimization(status="APPROVED")
    response = client.post(f"/optimizations/{opt_id}/approve?merchant_id=test_exec_merchant")
    assert response.status_code == 400

def test_5_execute_approved_and_test_14_successful_discount_update():
    opt_id = setup_optimization(status="APPROVED")
    response = client.post(f"/optimizations/{opt_id}/execute?merchant_id=test_exec_merchant")
    assert response.status_code == 200
    data = response.json()
    assert data["execution_status"] == "SUCCESS"
    assert data["changes"][0]["previous_value"] == 10.0
    assert data["changes"][0]["new_value"] == 15.0
    assert data["changes"][0]["offers_updated"] == 1
    
    # Verify DB
    opt = optimizations_collection.find_one({"optimization_id": opt_id})
    assert opt["status"] == "EXECUTED"

def test_6_cannot_execute_generated():
    opt_id = setup_optimization(status="GENERATED")
    response = client.post(f"/optimizations/{opt_id}/execute?merchant_id=test_exec_merchant")
    assert response.status_code == 400

def test_7_cannot_execute_rejected():
    opt_id = setup_optimization(status="REJECTED")
    response = client.post(f"/optimizations/{opt_id}/execute?merchant_id=test_exec_merchant")
    assert response.status_code == 400

def test_8_cannot_execute_already_executed_and_test_16_double_execution():
    opt_id = setup_optimization(status="APPROVED")
    # First execution
    response1 = client.post(f"/optimizations/{opt_id}/execute?merchant_id=test_exec_merchant")
    assert response1.status_code == 200
    
    # Second execution (Idempotent)
    response2 = client.post(f"/optimizations/{opt_id}/execute?merchant_id=test_exec_merchant")
    assert response2.status_code == 200
    # Should return exactly the same object
    assert response1.json()["execution_id"] == response2.json()["execution_id"]

def test_9_guardrail_blocks_stale():
    opt_id = setup_optimization(status="APPROVED", recs=[{
        "type": "discount_adjustment",
        "segment": "new_visitor",
        "recommended_change": "Increase to 25%",
        "reason": "Test",
        "priority": "high",
        "status": "GENERATED"
    }])
    # Originally maybe max_discount was 30, but now it's 20.
    response = client.post(f"/optimizations/{opt_id}/execute?merchant_id=test_exec_merchant")
    assert response.status_code == 200
    assert response.json()["execution_status"] == "FAILED"
    assert "exceeds current merchant safe limit" in response.json()["failure_reason"]
    
    opt = optimizations_collection.find_one({"optimization_id": opt_id})
    assert opt["status"] == "FAILED"

def test_10_unsupported_recommendation_type():
    opt_id = setup_optimization(status="APPROVED", recs=[{
        "type": "campaign_pause",
        "segment": "all",
        "recommended_change": "Pause campaign",
        "reason": "Test",
        "priority": "high",
        "status": "GENERATED"
    }])
    response = client.post(f"/optimizations/{opt_id}/execute?merchant_id=test_exec_merchant")
    assert response.status_code == 200
    assert response.json()["execution_status"] == "FAILED"
    assert "EXECUTION_NOT_SUPPORTED" in response.json()["failure_reason"]

def test_11_merchant_ownership():
    opt_id = setup_optimization(status="GENERATED")
    response = client.post(f"/optimizations/{opt_id}/approve?merchant_id=fake_merchant")
    assert response.status_code == 400

def test_12_optimization_not_found():
    response = client.post(f"/optimizations/fake_opt/approve?merchant_id=test_exec_merchant")
    assert response.status_code == 400

def test_13_invalid_discount_value():
    opt_id = setup_optimization(status="APPROVED", recs=[{
        "type": "discount_adjustment",
        "segment": "new_visitor",
        "recommended_change": "Make it free",
        "reason": "Test",
        "priority": "high",
        "status": "GENERATED"
    }])
    response = client.post(f"/optimizations/{opt_id}/execute?merchant_id=test_exec_merchant")
    assert response.status_code == 200
    assert response.json()["execution_status"] == "FAILED"
    assert "parse numeric" in response.json()["failure_reason"]

def test_15_execution_failure():
    # Force a failure (e.g. no segment)
    opt_id = setup_optimization(status="APPROVED", recs=[{
        "type": "discount_adjustment",
        "segment": "",
        "recommended_change": "10%",
        "reason": "Test",
        "priority": "high",
        "status": "GENERATED"
    }])
    response = client.post(f"/optimizations/{opt_id}/execute?merchant_id=test_exec_merchant")
    assert response.status_code == 200
    assert response.json()["execution_status"] == "FAILED"
    assert "Segment missing" in response.json()["failure_reason"]
