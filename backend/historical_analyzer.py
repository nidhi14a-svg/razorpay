from typing import Dict, Any, List
from database import campaigns_collection, offers_collection, orders_collection

def get_historical_learning_insights(merchant_id: str) -> Dict[str, Any]:
    """
    Analyzes historical campaigns to determine deterministic performance patterns.
    Produces a structure summarizing best/weak segments, discount performance, etc.
    """
    
    # Only analyze campaigns that have been COMPLETED
    completed_campaigns = list(campaigns_collection.find({"merchant_id": merchant_id, "status": "COMPLETED"}))
    campaign_ids = [c["campaign_id"] for c in completed_campaigns]
    campaigns_analyzed = len(campaign_ids)
    
    insights = {
        "campaigns_analyzed": campaigns_analyzed,
        "best_segments": [],
        "weak_segments": [],
        "best_offers": [],
        "discount_insights": [],
        "performance_patterns": [],
        "data_quality": {
            "confidence": "low",
            "reason": "No historical campaigns available."
        }
    }
    
    if campaigns_analyzed == 0:
        return insights
        
    if campaigns_analyzed == 1:
        insights["data_quality"] = {
            "confidence": "low",
            "reason": "Only one historical campaign available. Evidence is limited."
        }
    elif campaigns_analyzed < 3:
        insights["data_quality"] = {
            "confidence": "medium",
            "reason": "Some historical data available, but not extensive."
        }
    else:
        insights["data_quality"] = {
            "confidence": "high",
            "reason": "Strong historical evidence from multiple campaigns."
        }
        
    # Aggregate data by segment
    segment_pipeline = [
        {"$match": {"merchant_id": merchant_id, "campaign_id": {"$in": campaign_ids}}},
        {"$lookup": {
            "from": "orders",
            "localField": "offer_id",
            "foreignField": "offer_id",
            "as": "order"
        }},
        {"$unwind": {"path": "$order", "preserveNullAndEmptyArrays": True}},
        {"$group": {
            "_id": "$customer_segment",
            "offers_sent": {"$addToSet": "$offer_id"},
            "orders": {"$sum": {"$cond": [{"$ifNull": ["$order._id", False]}, 1, 0]}},
            "revenue_paise": {"$sum": {"$cond": [{"$eq": ["$order.payment_status", "PAYMENT_VERIFIED"]}, "$order.amount", 0]}}
        }}
    ]
    
    segment_results = list(offers_collection.aggregate(segment_pipeline))
    
    for row in segment_results:
        segment = row.get("_id")
        offers_sent = len(row.get("offers_sent", []))
        orders = row.get("orders", 0)
        revenue = row.get("revenue_paise", 0) / 100.0
        
        conversion_rate = (orders / offers_sent * 100) if offers_sent > 0 else 0
        
        stat_obj = {
            "segment": segment,
            "offers_sent": offers_sent,
            "orders": orders,
            "conversion_rate": round(conversion_rate, 2),
            "revenue": round(revenue, 2)
        }
        
        if offers_sent > 0:
            if conversion_rate >= 10: # threshold for strong
                insights["best_segments"].append(stat_obj)
            elif conversion_rate < 2 and offers_sent >= 5: # threshold for weak
                insights["weak_segments"].append(stat_obj)
                
    # Aggregate data by discount_percentage
    discount_pipeline = [
        {"$match": {"merchant_id": merchant_id, "campaign_id": {"$in": campaign_ids}}},
        {"$lookup": {
            "from": "orders",
            "localField": "offer_id",
            "foreignField": "offer_id",
            "as": "order"
        }},
        {"$unwind": {"path": "$order", "preserveNullAndEmptyArrays": True}},
        {"$group": {
            "_id": "$discount_percentage",
            "offers_sent": {"$addToSet": "$offer_id"},
            "orders": {"$sum": {"$cond": [{"$ifNull": ["$order._id", False]}, 1, 0]}},
            "revenue_paise": {"$sum": {"$cond": [{"$eq": ["$order.payment_status", "PAYMENT_VERIFIED"]}, "$order.amount", 0]}}
        }}
    ]
    
    discount_results = list(offers_collection.aggregate(discount_pipeline))
    
    for row in discount_results:
        discount_pct = row.get("_id")
        offers_sent = len(row.get("offers_sent", []))
        orders = row.get("orders", 0)
        revenue = row.get("revenue_paise", 0) / 100.0
        
        conversion_rate = (orders / offers_sent * 100) if offers_sent > 0 else 0
        
        insights["discount_insights"].append({
            "discount_percentage": discount_pct,
            "offers_sent": offers_sent,
            "orders": orders,
            "conversion_rate": round(conversion_rate, 2),
            "revenue": round(revenue, 2)
        })
        
    # Sort for best insights
    insights["best_segments"] = sorted(insights["best_segments"], key=lambda x: x["conversion_rate"], reverse=True)
    insights["discount_insights"] = sorted(insights["discount_insights"], key=lambda x: x["conversion_rate"], reverse=True)
    
    # Generate some simple patterns
    if insights["best_segments"]:
        top_segment = insights["best_segments"][0]
        insights["performance_patterns"].append(f"The {top_segment['segment']} segment has historically converted best at {top_segment['conversion_rate']}%.")
        
    if insights["weak_segments"]:
        weak_segment = insights["weak_segments"][0]
        insights["performance_patterns"].append(f"The {weak_segment['segment']} segment consistently underperforms with only {weak_segment['conversion_rate']}% conversion despite receiving {weak_segment['offers_sent']} offers.")

    return insights
