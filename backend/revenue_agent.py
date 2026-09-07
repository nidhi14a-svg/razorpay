from typing import Dict, Any
from datetime import datetime, timezone
import uuid
from database import merchants_collection, customers_collection, agent_runs_collection
from merchant_intelligence import get_merchant_campaign_intelligence
from claude_agent import generate_revenue_recommendation
from guardrails import validate_offer
from historical_analyzer import get_historical_learning_insights
from recommendation_scorer import evaluate_recommendation

def run_revenue_agent(merchant_id: str) -> Dict[str, Any]:
    """
    Holistic AI Revenue Agent distinguishing between:
      1. MISSING_GUARDRAILS
      2. INSUFFICIENT_CUSTOMER_DATA
      3. INSUFFICIENT_BEHAVIORAL_DATA
      4. READY
    """
    # 1. Collect Business Context
    merchant = merchants_collection.find_one({"merchant_id": merchant_id})
    if not merchant:
        raise ValueError("Merchant not found")
        
    merchant_rules = merchant.get("rules")
    # State 1: MISSING_GUARDRAILS
    if (not merchant_rules or 
        merchant_rules.get("max_discount_percentage") is None or 
        merchant_rules.get("min_margin_percentage") is None):
        run_id = f"run_{uuid.uuid4()}"
        result = {
            "agent_run_id": run_id,
            "merchant_id": merchant_id,
            "status": "MISSING_GUARDRAILS",
            "data_sufficiency": "MISSING_GUARDRAILS",
            "strategy": "Configure Merchant Guardrails",
            "recommendation": None,
            "reason": "Merchant has not configured maximum discount and minimum margin guardrails.",
            "evidence": ["Merchant guardrail rules are not configured."],
            "confidence": "low",
            "guardrail_result": {"status": "REJECTED", "reason": "Merchant guardrails missing"}
        }
        agent_runs_collection.insert_one({
            **result,
            "timestamp": datetime.now(timezone.utc)
        })
        return result

    # State 2: NO_CUSTOMER_DATA
    total_customers = customers_collection.count_documents({"merchant_id": merchant_id})
    if total_customers == 0:
        run_id = f"run_{uuid.uuid4()}"
        result = {
            "agent_run_id": run_id,
            "merchant_id": merchant_id,
            "status": "NO_CUSTOMER_DATA",
            "data_sufficiency": "NO_CUSTOMER_DATA",
            "strategy": "Upload Customer Dataset",
            "recommendation": None,
            "reason": "No customer data has been uploaded. Please import your customer or transaction dataset.",
            "evidence": ["0 customer records found in database."],
            "confidence": "low",
            "guardrail_result": {"status": "SKIPPED", "reason": "No customer data"}
        }
        agent_runs_collection.insert_one({
            **result,
            "timestamp": datetime.now(timezone.utc)
        })
        return result

    # State 3: INSUFFICIENT_BEHAVIORAL_DATA
    valid_behavioral_count = customers_collection.count_documents({
        "merchant_id": merchant_id,
        "$or": [
            {"purchase_count": {"$gt": 0}},
            {"lifetime_value": {"$gt": 0}}
        ]
    })
    if valid_behavioral_count == 0:
        run_id = f"run_{uuid.uuid4()}"
        result = {
            "agent_run_id": run_id,
            "merchant_id": merchant_id,
            "status": "INSUFFICIENT_BEHAVIORAL_DATA",
            "data_sufficiency": "INSUFFICIENT_BEHAVIORAL_DATA",
            "strategy": "Upload Transactional Data",
            "recommendation": None,
            "reason": (
                "Customer records exist, but purchase history could not be calculated because the "
                "uploaded dataset contains demographic data only (e.g., customer IDs, city, state) "
                "and lacks order transaction amounts, prices, or purchase history."
            ),
            "evidence": [f"{total_customers} customer records exist, but all have 0 purchases and 0 lifetime value."],
            "confidence": "low",
            "guardrail_result": {"status": "SKIPPED", "reason": "No behavioral purchase data"}
        }
        agent_runs_collection.insert_one({
            **result,
            "timestamp": datetime.now(timezone.utc)
        })
        return result

    # State 4: READY - Guardrails and behavioral customer data exist
    segment_counts_cursor = customers_collection.aggregate([
        {"$match": {"merchant_id": merchant_id}},
        {"$group": {"_id": "$segment", "count": {"$sum": 1}}}
    ])
    segment_counts = {str(doc["_id"]): doc["count"] for doc in segment_counts_cursor if doc.get("_id")}
    
    intelligence = get_merchant_campaign_intelligence(merchant_id)
    historical_learning = get_historical_learning_insights(merchant_id)
    
    context = {
        "merchant_id": merchant_id,
        "merchant_rules": merchant_rules,
        "total_customers": total_customers,
        "segment_counts": segment_counts,
        "campaign_intelligence": intelligence,
        "historical_learning": historical_learning
    }
    
    # Generate recommendation
    ai_response = generate_revenue_recommendation(context)
    
    # Check for AI API failure fallback
    if ai_response.get("recommendation", {}).get("action") == "API failure fallback":
        run_id = f"run_{uuid.uuid4()}"
        result = {
            "agent_run_id": run_id,
            "merchant_id": merchant_id,
            "status": "FAILED",
            "data_sufficiency": "READY",
            "recommendation": None,
            "reason": "AI recommendation temporarily unavailable",
            "evidence": [],
            "confidence": "low",
            "guardrail_result": None
        }
        agent_runs_collection.insert_one({
            **result,
            "timestamp": datetime.now(timezone.utc)
        })
        return result
    
    recommendation = ai_response.get("recommendation", {})
    discount_pct = recommendation.get("discount_percentage", 0)
    target_segment = recommendation.get("segment", "loyal")
    raw_confidence = ai_response.get("confidence", "medium").lower()
    
    # Guardrail Validation
    mock_customer = {"purchase_count": 2, "lifetime_value": 500}
    if target_segment.lower() == "loyal":
        mock_customer["purchase_count"] = 5
    elif target_segment.lower() == "vip":
        mock_customer["purchase_count"] = 4
        mock_customer["lifetime_value"] = 2500
        
    offer_to_validate = {"discount_pct": discount_pct}
    is_approved = validate_offer(offer_to_validate, merchant_rules, mock_customer)
    
    run_id = f"run_{uuid.uuid4()}"
    
    if is_approved:
        reason = ai_response.get("reasoning", ai_response.get("reason", "Strategy generated successfully based on customer segments."))
        guardrail_result = {"status": "APPROVED", "reason": "Passed all merchant rules"}
        final_status = "READY"
    else:
        reason = "Recommended discount violates merchant maximum or minimum margin"
        guardrail_result = {"status": "REJECTED", "reason": reason}
        final_status = "REJECTED"
        
    # Deterministic Scoring
    scoring = evaluate_recommendation(recommendation, context, guardrail_result)
    
    final_result = {
        "agent_run_id": run_id,
        "merchant_id": merchant_id,
        "status": final_status,
        "data_sufficiency": "READY",
        "strategy": ai_response.get("strategy", "Revenue Optimization Strategy"),
        "priority": ai_response.get("priority", "medium"),
        "recommendation": recommendation,
        "reason": reason,
        "evidence": ai_response.get("evidence", [f"Analyzed {total_customers} customers across segments: {', '.join(segment_counts.keys())}"]),
        "confidence": raw_confidence,
        "guardrail_result": guardrail_result,
        "score": scoring.get("score", 85),
        "score_breakdown": scoring.get("score_breakdown", {}),
        "explanation": scoring.get("explanation", "")
    }
    
    # Persist the run
    agent_runs_collection.insert_one({
        **final_result,
        "timestamp": datetime.now(timezone.utc)
    })
    
    return final_result
