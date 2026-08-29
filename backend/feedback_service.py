import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from database import (
    optimizations_collection,
    campaigns_collection,
    feedback_collection
)
from analytics import get_campaign_analytics
from claude_agent import generate_feedback_interpretation

def evaluate_optimization_outcome(optimization_id: str, merchant_id: str) -> Dict[str, Any]:
    # 1. Idempotency Check / Retrieve Existing
    existing_feedback = feedback_collection.find_one({"optimization_id": optimization_id, "merchant_id": merchant_id})
    if existing_feedback:
        existing_feedback.pop("_id", None)
        return existing_feedback

    # 2. Validate Optimization exists and is owned
    opt = optimizations_collection.find_one({"optimization_id": optimization_id, "merchant_id": merchant_id})
    if not opt:
        raise ValueError("Optimization not found")

    # 3. Verify it was executed
    if opt.get("status") != "EXECUTED":
        raise ValueError(f"Cannot evaluate feedback for optimization with status: {opt.get('status')}")
        
    campaign_id = opt.get("campaign_id")
    campaign = campaigns_collection.find_one({"campaign_id": campaign_id, "merchant_id": merchant_id})
    if not campaign:
        raise ValueError("Campaign not found")

    # 4. Retrieve BEFORE metrics
    before_metrics = opt.get("campaign_metrics_snapshot")
    if not before_metrics or before_metrics.get("status") == "no_data":
        # Missing original snapshot data means we can't compare
        before_metrics = {
            "total_offers": 0,
            "verified_payments": 0,
            "revenue": 0.0,
            "conversion_rate": 0.0,
            "average_order_value": 0.0
        }

    # 5. Retrieve AFTER metrics
    after_metrics = get_campaign_analytics(campaign_id)
    if not after_metrics:
        raise ValueError("Cannot retrieve current campaign metrics")

    # 6. Calculate deterministic changes
    def get_val(data, key, default=0.0):
        try:
            return float(data.get(key, default))
        except (TypeError, ValueError):
            return float(default)

    b_conv = get_val(before_metrics, "conversion_rate")
    a_conv = get_val(after_metrics, "conversion_rate")
    conv_change = round(a_conv - b_conv, 2)

    b_rev = get_val(before_metrics, "revenue")
    a_rev = get_val(after_metrics, "revenue")
    rev_change = round(a_rev - b_rev, 2)
    
    b_vp = get_val(before_metrics, "verified_payments")
    a_vp = get_val(after_metrics, "verified_payments")
    vp_change = round(a_vp - b_vp, 2)
    
    b_aov = get_val(before_metrics, "average_order_value")
    a_aov = get_val(after_metrics, "average_order_value")
    aov_change = round(a_aov - b_aov, 2)

    changes = {
        "conversion_rate": conv_change,
        "revenue": rev_change,
        "verified_payments": vp_change,
        "average_order_value": aov_change
    }

    # 7. Classify the outcome
    a_offers = get_val(after_metrics, "total_offers")
    
    if a_offers == 0:
        outcome = "INSUFFICIENT_DATA"
    elif conv_change > 0.5 or rev_change > 0:
        outcome = "IMPROVED"
    elif conv_change < -0.5 or rev_change < 0:
        outcome = "DECLINED"
    else:
        outcome = "NO_SIGNIFICANT_CHANGE"

    # 8. AI Interpretation
    ai_interpretation = generate_feedback_interpretation(
        before_metrics=before_metrics,
        after_metrics=after_metrics,
        changes=changes,
        outcome=outcome
    )

    # 9. Persist Feedback
    feedback_id = str(uuid.uuid4())
    feedback_doc = {
        "feedback_id": feedback_id,
        "optimization_id": optimization_id,
        "campaign_id": campaign_id,
        "merchant_id": merchant_id,
        "before": {
            "timestamp": opt.get("generated_at"),
            "conversion_rate": b_conv,
            "revenue": b_rev,
            "total_offers": get_val(before_metrics, "total_offers"),
            "verified_payments": b_vp,
            "average_order_value": b_aov
        },
        "after": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "conversion_rate": a_conv,
            "revenue": a_rev,
            "total_offers": a_offers,
            "verified_payments": a_vp,
            "average_order_value": a_aov
        },
        "changes": changes,
        "outcome": outcome,
        "ai_interpretation": ai_interpretation,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    feedback_collection.insert_one(feedback_doc)
    
    # Return without Mongo _id
    feedback_doc.pop("_id", None)
    return feedback_doc
