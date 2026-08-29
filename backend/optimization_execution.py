import uuid
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from database import (
    optimizations_collection,
    optimization_executions_collection,
    merchants_collection,
    offers_collection,
    campaigns_collection
)
from optimization import get_max_safe_discount

def approve_optimization(optimization_id: str, merchant_id: str) -> Dict[str, Any]:
    opt = optimizations_collection.find_one({"optimization_id": optimization_id, "merchant_id": merchant_id})
    if not opt:
        raise ValueError("Optimization not found")
        
    if opt.get("status") != "GENERATED":
        raise ValueError(f"Cannot approve optimization with status: {opt.get('status')}")
        
    now = datetime.now(timezone.utc).isoformat()
    optimizations_collection.update_one(
        {"optimization_id": optimization_id},
        {"$set": {"status": "APPROVED", "approved_at": now}}
    )
    
    opt["status"] = "APPROVED"
    opt["approved_at"] = now
    opt.pop("_id", None)
    return opt

def reject_optimization(optimization_id: str, merchant_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    opt = optimizations_collection.find_one({"optimization_id": optimization_id, "merchant_id": merchant_id})
    if not opt:
        raise ValueError("Optimization not found")
        
    if opt.get("status") != "GENERATED":
        raise ValueError(f"Cannot reject optimization with status: {opt.get('status')}")
        
    now = datetime.now(timezone.utc).isoformat()
    update_data = {"status": "REJECTED", "rejected_at": now}
    if reason:
        update_data["rejection_reason"] = reason
        
    optimizations_collection.update_one(
        {"optimization_id": optimization_id},
        {"$set": update_data}
    )
    
    opt.update(update_data)
    opt.pop("_id", None)
    return opt

def execute_optimization(optimization_id: str, merchant_id: str) -> Dict[str, Any]:
    # 1. Idempotency Check
    existing_execution = optimization_executions_collection.find_one(
        {"optimization_id": optimization_id, "merchant_id": merchant_id},
        {"_id": 0}
    )
    if existing_execution:
        return existing_execution

    # 2. Validate Optimization State
    opt = optimizations_collection.find_one({"optimization_id": optimization_id, "merchant_id": merchant_id})
    if not opt:
        raise ValueError("Optimization not found")
        
    if opt.get("status") != "APPROVED":
        raise ValueError(f"Cannot execute optimization with status: {opt.get('status')}. Must be APPROVED.")

    campaign_id = opt.get("campaign_id")
    if not campaign_id:
        raise ValueError("Campaign ID missing from optimization record.")

    # 3. Retrieve Latest Merchant Rules
    merchant = merchants_collection.find_one({"merchant_id": merchant_id})
    if not merchant:
        raise ValueError("Merchant not found")
    
    merchant_rules = merchant.get("rules", {
        "max_discount_percentage": 20.0,
        "min_margin_percentage": 30.0
    })
    
    max_discount_rule = float(merchant_rules.get("max_discount_percentage", 20.0))
    min_margin_rule = float(merchant_rules.get("min_margin_percentage", 30.0))
    max_safe_discount = min(max_discount_rule, get_max_safe_discount(min_margin_rule))

    execution_id = str(uuid.uuid4())
    execution_record = {
        "execution_id": execution_id,
        "optimization_id": optimization_id,
        "campaign_id": campaign_id,
        "merchant_id": merchant_id,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "execution_status": "FAILED",
        "changes": []
    }

    try:
        # 4. Process Recommendations
        recommendations = opt.get("recommendations", [])
        if not recommendations:
            raise ValueError("No recommendations to execute")

        for rec in recommendations:
            rec_type = rec.get("type")
            
            # Currently only supporting discount_adjustment
            if rec_type != "discount_adjustment":
                raise ValueError("EXECUTION_NOT_SUPPORTED")
                
            segment = rec.get("segment")
            if not segment:
                raise ValueError("Segment missing in recommendation")

            # Try to extract discount value from string
            recommended_change_text = rec.get("recommended_change", "")
            
            # Reject if we see negative values
            if re.findall(r'-\d+', recommended_change_text):
                raise ValueError("Guardrail violation: Negative discount recommended")
                
            numbers = re.findall(r'\d+', recommended_change_text)
            if not numbers:
                raise ValueError("Could not parse numeric discount value from recommendation")
                
            new_discount = max([float(n) for n in numbers])
            
            # 5. Re-check Guardrails
            if new_discount > max_safe_discount:
                raise ValueError(f"Guardrail violation: Stale recommendation. Recommended discount ({new_discount}%) exceeds current merchant safe limit ({max_safe_discount}%)")

            # 6. Execute change: Update all matching offers
            # Assuming we find the current discount to record previous_value
            # For simplicity, if we update multiple offers, we'll record the change action generally.
            # In a robust system, we might update the Campaign configuration, but our offers are pre-generated.
            # We'll update the discount_percentage on pending offers for this campaign and segment.
            
            query = {
                "campaign_id": campaign_id,
                "merchant_id": merchant_id,
                "customer_segment": segment,
                "status": {"$in": ["OFFER_CREATED", "VIEWED"]}
            }
            
            # Find an example offer to get previous value
            example_offer = offers_collection.find_one(query)
            previous_value = example_offer.get("discount_percentage", 0.0) if example_offer else None

            # Perform the update
            update_result = offers_collection.update_many(
                query,
                {"$set": {"discount_percentage": new_discount}}
            )
            
            execution_record["changes"].append({
                "segment": segment,
                "previous_value": previous_value,
                "new_value": new_discount,
                "offers_updated": update_result.modified_count
            })

        execution_record["execution_status"] = "SUCCESS"
        optimizations_collection.update_one(
            {"optimization_id": optimization_id},
            {"$set": {"status": "EXECUTED"}}
        )

    except ValueError as ve:
        execution_record["execution_status"] = "FAILED"
        execution_record["failure_reason"] = str(ve)
        optimizations_collection.update_one(
            {"optimization_id": optimization_id},
            {"$set": {"status": "FAILED"}}
        )
    except Exception as e:
        execution_record["execution_status"] = "FAILED"
        execution_record["failure_reason"] = f"Internal execution error: {str(e)}"
        optimizations_collection.update_one(
            {"optimization_id": optimization_id},
            {"$set": {"status": "FAILED"}}
        )
        
    optimization_executions_collection.insert_one(execution_record)
    execution_record.pop("_id", None)
    return execution_record

