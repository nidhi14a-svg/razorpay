from typing import Dict, Any, List
from database import merchants_collection, campaigns_collection, feedback_collection
from analytics import get_merchant_historical_performance, get_merchant_segment_performance, get_campaign_analytics
from claude_agent import generate_merchant_insights

def get_merchant_campaign_intelligence(merchant_id: str) -> Dict[str, Any]:
    # 1. Validate merchant
    merchant = merchants_collection.find_one({"merchant_id": merchant_id})
    if not merchant:
        raise ValueError("Merchant not found")

    # 2. Summary (using existing analytics)
    hist_perf = get_merchant_historical_performance(merchant_id)
    summary = {
        "total_campaigns": hist_perf.get("total_campaigns", 0),
        "total_offers": hist_perf.get("total_offers", 0),
        "total_payments": hist_perf.get("verified_payments", 0),
        "total_revenue": hist_perf.get("revenue", 0.0),
        "average_conversion_rate": hist_perf.get("conversion_rate", 0.0),
        "average_order_value": hist_perf.get("average_order_value", 0.0)
    }

    # 3. Campaign Comparison
    campaigns_cursor = campaigns_collection.find({"merchant_id": merchant_id})
    campaign_comparison = []
    
    best_campaign = None
    lowest_campaign = None

    for camp in campaigns_cursor:
        camp_id = camp.get("campaign_id")
        camp_analytics = get_campaign_analytics(camp_id)
        if camp_analytics:
            data = {
                "campaign_id": camp_id,
                "campaign_name": camp.get("campaign_name", "Unknown"),
                "target_segment": camp.get("target_segment", "all"),
                "offers": camp_analytics.get("total_offers", 0),
                "payments": camp_analytics.get("verified_payments", 0),
                "conversion_rate": camp_analytics.get("conversion_rate", 0.0),
                "revenue": camp_analytics.get("revenue", 0.0),
                "average_order_value": camp_analytics.get("average_order_value", 0.0)
            }
            campaign_comparison.append(data)
            
            # Only consider campaigns with some data for best/lowest
            if data["offers"] >= 5:
                if best_campaign is None or data["conversion_rate"] > best_campaign["conversion_rate"]:
                    best_campaign = data
                if lowest_campaign is None or data["conversion_rate"] < lowest_campaign["conversion_rate"]:
                    lowest_campaign = data

    # 4. Segment Intelligence
    segment_perf = get_merchant_segment_performance(merchant_id)
    segment_intelligence = []
    for sp in segment_perf:
        segment_intelligence.append({
            "segment": sp.get("segment"),
            "offers": sp.get("total_offers"),
            "payments": sp.get("verified_payments"),
            "conversion_rate": sp.get("conversion_rate"),
            "revenue": sp.get("revenue")
        })

    # 5. Offer Intelligence
    # Since the database doesn't currently structure abstract offer categories (like BOGO vs Flat),
    # we explicitly report insufficient offer-level data as per requirements.
    offer_intelligence = "insufficient offer-level data"

    # 6. Optimization Outcome Intelligence & Before/After Learning
    feedback_cursor = feedback_collection.find({"merchant_id": merchant_id})
    feedbacks = list(feedback_cursor)
    
    opt_history = {
        "total_optimizations": len(feedbacks),
        "executed": len(feedbacks), # feedback is only evaluated on executed
        "improved": sum(1 for f in feedbacks if f.get("outcome") == "IMPROVED"),
        "declined": sum(1 for f in feedbacks if f.get("outcome") == "DECLINED"),
        "no_significant_change": sum(1 for f in feedbacks if f.get("outcome") == "NO_SIGNIFICANT_CHANGE"),
        "insufficient_data": sum(1 for f in feedbacks if f.get("outcome") == "INSUFFICIENT_DATA")
    }

    before_after_learning = []
    if opt_history["improved"] > 0:
        before_after_learning.append("Historical data suggests that recent optimization changes have generally led to IMPROVED performance in available observations.")
    elif opt_history["declined"] > 0:
        before_after_learning.append("Historical data suggests that some recent optimization changes were followed by a DECLINE in performance.")
    else:
        before_after_learning.append("No conclusive deterministic patterns observed in optimization history yet.")

    # Determine Cold Start
    is_cold_start = (summary["total_campaigns"] <= 1 and summary["total_offers"] < 5 and opt_history["total_optimizations"] == 0)

    # Compile deterministic data
    deterministic_data = {
        "summary": summary,
        "campaign_comparison": campaign_comparison,
        "best_performing_campaign": best_campaign,
        "lowest_performing_campaign": lowest_campaign,
        "segment_intelligence": segment_intelligence,
        "offer_intelligence": offer_intelligence,
        "optimization_history": opt_history,
        "before_after_learning": before_after_learning
    }

    if is_cold_start:
        ai_insights = {
            "summary": "INSUFFICIENT_DATA",
            "key_findings": ["Not enough data to analyze"],
            "opportunities": [],
            "warnings": []
        }
    else:
        ai_insights = generate_merchant_insights(deterministic_data)

    return {
        "merchant_id": merchant_id,
        "summary": summary,
        "campaign_comparison": campaign_comparison,
        "best_performing_campaign": best_campaign,
        "lowest_performing_campaign": lowest_campaign,
        "segment_intelligence": segment_intelligence,
        "offer_intelligence": offer_intelligence,
        "optimization_history": opt_history,
        "before_after_learning": before_after_learning,
        "ai_insights": ai_insights
    }
