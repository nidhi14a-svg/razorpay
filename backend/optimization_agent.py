from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timezone

from database import optimizations_collection, campaigns_collection, merchants_collection
from analytics import get_campaign_analytics, get_campaign_segment_analytics, get_merchant_historical_performance
from claude_agent import generate_optimization_recommendations
from optimization import get_max_safe_discount
from database import feedback_collection

class Recommendation(BaseModel):
    type: str
    segment: str
    recommended_change: str
    reason: str
    priority: str
    status: Optional[str] = "GENERATED"

class OptimizationSchema(BaseModel):
    overall_assessment: str
    recommendations: List[Recommendation]

def analyze_campaign_for_optimization(campaign_id: str, merchant_id: str) -> Dict[str, Any]:
    """
    Analyzes a campaign and generates optimization recommendations.
    Applies deterministic safety checks to reject unsafe recommendations.
    Persists the recommendation and metrics snapshot to MongoDB.
    """
    # 1. Validate Campaign
    campaign = campaigns_collection.find_one({"campaign_id": campaign_id, "merchant_id": merchant_id})
    if not campaign:
        raise ValueError("Campaign not found")

    # 2. Retrieve Merchant Rules
    merchant = merchants_collection.find_one({"merchant_id": merchant_id})
    if not merchant:
        raise ValueError("Merchant not found")
    
    merchant_rules = merchant.get("rules", {
        "max_discount_percentage": 20.0,
        "min_margin_percentage": 30.0
    })

    # 3. Retrieve Metrics
    campaign_metrics = get_campaign_analytics(campaign_id)
    if not campaign_metrics:
        # Should not happen if campaign exists, but safe fallback
        campaign_metrics = {"status": "no_data"}
        
    segment_metrics = get_campaign_segment_analytics(campaign_id) or []
    historical_performance = get_merchant_historical_performance(merchant_id)

    campaign_context = {
        "campaign_id": campaign_id,
        "name": campaign.get("campaign_name", "Unknown"),
        "target": campaign.get("target_segment", "All")
    }
    
    # Retrieve up to 5 previous feedback outcomes for this merchant
    previous_feedbacks_cursor = feedback_collection.find({"merchant_id": merchant_id}).sort("created_at", -1).limit(5)
    previous_feedbacks = []
    for fb in previous_feedbacks_cursor:
        previous_feedbacks.append({
            "optimization_id": fb.get("optimization_id"),
            "campaign_id": fb.get("campaign_id"),
            "changes_made": fb.get("changes"),
            "outcome": fb.get("outcome"),
            "ai_interpretation": fb.get("ai_interpretation")
        })
        
    campaign_context["historical_optimization_feedback"] = previous_feedbacks if previous_feedbacks else "No previous optimization feedback available. Cold start."

    # 4. Generate AI Recommendations
    ai_response = generate_optimization_recommendations(
        campaign_metrics=campaign_metrics,
        segment_metrics=segment_metrics,
        historical_performance=historical_performance,
        merchant_rules=merchant_rules,
        campaign_context=campaign_context
    )

    # 5. Validate AI Schema and Guardrails
    try:
        parsed = OptimizationSchema(**ai_response)
    except Exception as e:
        print(f"Failed to parse optimization schema: {e}")
        # Return graceful failure if AI returns garbage
        parsed = OptimizationSchema(
            overall_assessment="Failed to generate valid optimization due to malformed AI response.",
            recommendations=[]
        )

    # Deterministic Guardrail Check
    max_discount_rule = float(merchant_rules.get("max_discount_percentage", 20.0))
    min_margin_rule = float(merchant_rules.get("min_margin_percentage", 30.0))
    max_safe_discount = min(max_discount_rule, get_max_safe_discount(min_margin_rule))

    valid_segments = ["loyal", "new_visitor", "cart_abandoned", "high_value", "price_sensitive", "dormant", "regular", "unknown", "all"]

    for rec in parsed.recommendations:
        # Check valid segment
        if rec.segment not in valid_segments:
            rec.status = "REJECTED_BY_GUARDRAIL"
            rec.reason += " [REJECTED: Invalid segment]"
            continue
            
        # Example naive check: if the recommendation suggests a discount adjustment, 
        # try to parse the number out of 'recommended_change' to see if it violates max discount.
        # A more robust system would require the AI to return the specific discount number as a float field.
        if rec.type == "discount_adjustment":
            import re
            # look for negative values
            neg_numbers = re.findall(r'-\d+', rec.recommended_change)
            if neg_numbers:
                rec.status = "REJECTED_BY_GUARDRAIL"
                rec.reason += " [REJECTED: Negative discount recommended]"
                continue
                
            numbers = re.findall(r'\d+', rec.recommended_change)
            if numbers:
                # Get the largest number mentioned as a conservative check
                max_num_found = max([float(n) for n in numbers])
                if max_num_found > max_safe_discount:
                    rec.status = "REJECTED_BY_GUARDRAIL"
                    rec.reason += f" [REJECTED: Recommended discount ({max_num_found}%) exceeds merchant safe limit ({max_safe_discount}%)]"

    # 6. Persist to MongoDB
    optimization_id = str(uuid.uuid4())
    optimization_doc = {
        "optimization_id": optimization_id,
        "campaign_id": campaign_id,
        "merchant_id": merchant_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "campaign_metrics_snapshot": campaign_metrics,
        "segment_metrics_snapshot": segment_metrics,
        "recommendations": [rec.model_dump() for rec in parsed.recommendations],
        "overall_assessment": parsed.overall_assessment,
        "status": "GENERATED"
    }
    
    optimizations_collection.insert_one(optimization_doc)

    return {
        "optimization_id": optimization_id,
        "campaign_id": campaign_id,
        "overall_assessment": parsed.overall_assessment,
        "recommendations": optimization_doc["recommendations"],
        "status": "GENERATED"
    }
