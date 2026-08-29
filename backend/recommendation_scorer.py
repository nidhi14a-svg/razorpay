from typing import Dict, Any, Tuple

def evaluate_recommendation(
    recommendation: Dict[str, Any],
    context: Dict[str, Any],
    guardrail_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Deterministically scores a recommendation based on available business signals.
    Returns {score, score_breakdown, explanation}.
    """
    breakdown = {
        "data_quality": 0,
        "historical_evidence": 0,
        "current_performance": 0,
        "rule_compatibility": 0
    }
    explanation = []
    
    target_segment = recommendation.get("segment", "").lower()
    recommended_discount = recommendation.get("discount_percentage", 0)
    
    historical = context.get("historical_learning", {})
    intelligence = context.get("campaign_intelligence", {})
    
    # 1. Data Sufficiency (Max 20)
    data_conf = historical.get("data_quality", {}).get("confidence", "low")
    if data_conf == "high":
        breakdown["data_quality"] = 20
        explanation.append("Recommendation is supported by strong historical data.")
    elif data_conf == "medium":
        breakdown["data_quality"] = 10
        explanation.append("Recommendation has limited historical data support.")
    else:
        breakdown["data_quality"] = 0
        explanation.append("No strong historical data available to support recommendation.")
        
    # 2. Historical Evidence (Max 30)
    best_segments = [s.get("segment", "").lower() for s in historical.get("best_segments", [])]
    weak_segments = [s.get("segment", "").lower() for s in historical.get("weak_segments", [])]
    
    if target_segment in best_segments:
        breakdown["historical_evidence"] += 15
        explanation.append(f"The {target_segment} segment has historically performed well.")
    elif target_segment in weak_segments:
        explanation.append(f"Note: The {target_segment} segment has historically underperformed.")
        
    # Check discount performance
    top_discounts = []
    for d_insight in historical.get("discount_insights", []):
        if d_insight.get("conversion_rate", 0) > 5.0: # threshold for "good" discount
            top_discounts.append(d_insight.get("discount_percentage"))
            
    if recommended_discount in top_discounts:
        breakdown["historical_evidence"] += 15
        explanation.append(f"A {recommended_discount}% discount aligns with historically successful campaigns.")
        
    # 3. Current Performance (Max 30)
    seg_intel = intelligence.get("segment_intelligence", [])
    target_seg_stats = next((s for s in seg_intel if s.get("segment", "").lower() == target_segment), None)
    
    if target_seg_stats:
        breakdown["current_performance"] += 15
        explanation.append("Recommendation targets a segment that is active in current campaigns.")
        
        # Does it address poor performance?
        avg_conv = intelligence.get("summary", {}).get("average_conversion_rate", 0)
        seg_conv = target_seg_stats.get("conversion_rate", 0)
        
        if seg_conv < avg_conv or seg_conv < 5.0:
            breakdown["current_performance"] += 15
            explanation.append("The recommendation addresses below-average current conversion for this segment.")
    else:
        if intelligence.get("summary", {}).get("total_campaigns", 0) > 0:
            explanation.append(f"The {target_segment} segment has no significant activity in current campaigns.")
        
    # 4. Rule Compatibility (Max 20)
    is_rejected = False
    if guardrail_result.get("status") == "APPROVED":
        breakdown["rule_compatibility"] = 20
        explanation.append("Recommended discount is within merchant limits.")
    else:
        breakdown["rule_compatibility"] = 0
        explanation.append("Recommendation violates merchant business rules.")
        is_rejected = True
        
    # Total Score
    total_score = sum(breakdown.values())
    
    # Fatal override
    if is_rejected:
        total_score = 0
        
    return {
        "score": total_score,
        "score_breakdown": breakdown,
        "explanation": explanation
    }
