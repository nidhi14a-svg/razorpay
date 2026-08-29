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
    """Orchestrates the Revenue Agent workflow for a given merchant."""
    
    # 1. Collect Business Context
    merchant = merchants_collection.find_one({"merchant_id": merchant_id})
    if not merchant:
        raise ValueError("Merchant not found")
        
    merchant_rules = merchant.get("rules", {
        "max_discount_percentage": 20.0,
        "min_margin_percentage": 30.0
    })
    
    segment_counts_cursor = customers_collection.aggregate([
        {"$match": {"merchant_id": merchant_id}},
        {"$group": {"_id": "$segment", "count": {"$sum": 1}}}
    ])
    segment_counts = {str(doc["_id"]): doc["count"] for doc in segment_counts_cursor if doc.get("_id")}
    total_customers = sum(segment_counts.values())
    
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
    
    # 2. Determine Data Sufficiency
    # If 0 campaigns, it's strictly INSUFFICIENT_DATA
    total_campaigns = intelligence.get("summary", {}).get("total_campaigns", 0)
    total_offers = intelligence.get("summary", {}).get("total_offers", 0)
    
    if total_campaigns == 0:
        data_status = "INSUFFICIENT_DATA"
    elif total_offers == 0:
        data_status = "LIMITED_DATA"
    else:
        data_status = "SUFFICIENT_DATA"
        
    if data_status == "INSUFFICIENT_DATA":
        # Pass INSUFFICIENT_DATA context to the LLM to allow it to reason about wait/test strategies
        pass
        
    # 3. LLM Analysis
    ai_response = generate_revenue_recommendation(context)
    
    # Check for AI API failure fallback
    if ai_response.get("recommendation", {}).get("action") == "API failure fallback":
        run_id = f"run_{uuid.uuid4()}"
        result = {
            "agent_run_id": run_id,
            "merchant_id": merchant_id,
            "status": "FAILED",
            "data_sufficiency": data_status,
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
    target_segment = recommendation.get("segment", "unknown")
    raw_confidence = ai_response.get("confidence", "low").lower()
    
    # Confidence Calibration based on deterministic data
    historical_confidence = historical_learning.get("data_quality", {}).get("confidence", "low")
    
    if data_status == "LIMITED_DATA":
        final_confidence = "low" if raw_confidence == "low" else "medium"
    else:
        final_confidence = raw_confidence # SUFFICIENT_DATA
        
    # Cap confidence based on historical data quality if they are analyzing historicals
    if historical_confidence == "low" and final_confidence == "high":
        final_confidence = "medium"
    elif historical_confidence == "low" and final_confidence == "medium":
        final_confidence = "low"
    
    # 4. Guardrail Validation
    # Synthesize a mock customer to test the segment properly through guardrails
    mock_customer = {"purchase_count": 0}
    if target_segment.lower() == "loyal":
        mock_customer["purchase_count"] = 5
    elif target_segment.lower() == "regular":
        mock_customer["purchase_count"] = 2
        
    offer_to_validate = {"discount_pct": discount_pct}
    
    is_approved = validate_offer(offer_to_validate, merchant_rules, mock_customer)
    
    run_id = f"run_{uuid.uuid4()}"
    
    if is_approved:
        reason = ai_response.get("reasoning", ai_response.get("reason", ""))
        guardrail_result = {"status": "APPROVED", "reason": "Passed all merchant rules"}
    else:
        reason = "Recommended discount violates merchant maximum or minimum margin"
        guardrail_result = {"status": "REJECTED", "reason": reason}
        
    # 5. Deterministic Scoring
    scoring = evaluate_recommendation(recommendation, context, guardrail_result)
    
    # 6. Final Status Evaluation
    if not is_approved:
        status = "REJECTED"
    elif data_status == "INSUFFICIENT_DATA":
        status = "INSUFFICIENT_DATA"
    else:
        status = "VALIDATED"
        
    final_result = {
        "agent_run_id": run_id,
        "merchant_id": merchant_id,
        "status": status,
        "data_sufficiency": data_status,
        "strategy": ai_response.get("strategy"),
        "priority": ai_response.get("priority", "medium"),
        "recommendation": recommendation,
        "reason": reason,
        "evidence": ai_response.get("evidence", []),
        "confidence": final_confidence,
        "guardrail_result": guardrail_result,
        "score": scoring["score"],
        "score_breakdown": scoring["score_breakdown"],
        "explanation": scoring["explanation"]
    }
    
    # Persist the run
    agent_runs_collection.insert_one({
        **final_result,
        "timestamp": datetime.now(timezone.utc)
    })
    
    return final_result
