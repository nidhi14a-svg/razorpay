from typing import Optional, List, Dict, Any
from database import offers_collection, campaigns_collection

def get_campaign_analytics(campaign_id: str) -> Optional[Dict[str, Any]]:
    """Calculates overall metrics for a specific campaign."""
    campaign = campaigns_collection.find_one({"campaign_id": campaign_id})
    if not campaign:
        return None
        
    pipeline = _build_analytics_pipeline(campaign_id, group_by_segment=False)
    results = list(offers_collection.aggregate(pipeline))
    
    if not results:
        # Campaign exists but has no offers yet
        return _format_analytics_result(campaign_id, None)
        
    return _format_analytics_result(campaign_id, results[0])

def get_campaign_segment_analytics(campaign_id: str) -> Optional[List[Dict[str, Any]]]:
    """Calculates metrics broken down by customer segment."""
    campaign = campaigns_collection.find_one({"campaign_id": campaign_id})
    if not campaign:
        return None
        
    pipeline = _build_analytics_pipeline(campaign_id, group_by_segment=True)
    results = list(offers_collection.aggregate(pipeline))
    
    formatted_results = []
    for res in results:
        segment = res.get("_id", "unknown")
        formatted = _format_analytics_result(campaign_id, res)
        formatted["segment"] = segment
        # Remove campaign_id to match the example format requested for segments
        formatted.pop("campaign_id", None)
        formatted_results.append(formatted)
        
    return formatted_results

def _build_analytics_pipeline(campaign_id: str, group_by_segment: bool) -> List[Dict[str, Any]]:
    group_id = "$customer_segment" if group_by_segment else None
    
    return [
        {"$match": {"campaign_id": campaign_id}},
        {"$lookup": {
            "from": "orders",
            "localField": "offer_id",
            "foreignField": "offer_id",
            "as": "order"
        }},
        # Unwind orders so we can calculate sums cleanly. 
        # preserveNullAndEmptyArrays ensures offers with NO orders are still counted.
        {"$unwind": {"path": "$order", "preserveNullAndEmptyArrays": True}},
        {"$group": {
            "_id": group_id,
            "customers_set": {"$addToSet": "$customer_id"},
            "offers_set": {"$addToSet": "$offer_id"},
            "total_orders": {
                "$sum": {"$cond": [{"$ifNull": ["$order._id", False]}, 1, 0]}
            },
            "verified_payments": {
                "$sum": {"$cond": [{"$eq": ["$order.payment_status", "PAYMENT_VERIFIED"]}, 1, 0]}
            },
            "failed_payments": {
                "$sum": {"$cond": [{"$eq": ["$order.payment_status", "PAYMENT_FAILED"]}, 1, 0]}
            },
            "total_revenue_paise": {
                "$sum": {"$cond": [{"$eq": ["$order.payment_status", "PAYMENT_VERIFIED"]}, "$order.amount", 0]}
            }
        }}
    ]

def _format_analytics_result(campaign_id: str, raw_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not raw_result:
        return {
            "campaign_id": campaign_id,
            "total_customers": 0,
            "total_offers": 0,
            "total_orders": 0,
            "verified_payments": 0,
            "failed_payments": 0,
            "revenue": 0.0,
            "conversion_rate": 0.0,
            "average_order_value": 0.0
        }
        
    total_customers = len(raw_result.get("customers_set", []))
    total_offers = len(raw_result.get("offers_set", []))
    total_orders = raw_result.get("total_orders", 0)
    verified_payments = raw_result.get("verified_payments", 0)
    failed_payments = raw_result.get("failed_payments", 0)
    
    # Revenue is stored in paise in the DB, so we convert back to INR for the frontend
    revenue_inr = raw_result.get("total_revenue_paise", 0) / 100.0
    
    conversion_rate = 0.0
    if total_offers > 0:
        conversion_rate = (verified_payments / total_offers) * 100.0
        
    average_order_value = 0.0
    if verified_payments > 0:
        average_order_value = revenue_inr / verified_payments
        
    return {
        "campaign_id": campaign_id,
        "total_customers": total_customers,
        "total_offers": total_offers,
        "total_orders": total_orders,
        "verified_payments": verified_payments,
        "failed_payments": failed_payments,
        "revenue": round(revenue_inr, 2),
        "conversion_rate": round(conversion_rate, 2),
        "average_order_value": round(average_order_value, 2)
    }

def _build_merchant_analytics_pipeline(merchant_id: str, group_by_segment: bool) -> List[Dict[str, Any]]:
    group_id = "$customer_segment" if group_by_segment else None
    
    return [
        {"$match": {"merchant_id": merchant_id}},
        {"$lookup": {
            "from": "orders",
            "localField": "offer_id",
            "foreignField": "offer_id",
            "as": "order"
        }},
        {"$unwind": {"path": "$order", "preserveNullAndEmptyArrays": True}},
        {"$group": {
            "_id": group_id,
            "customers_set": {"$addToSet": "$customer_id"},
            "offers_set": {"$addToSet": "$offer_id"},
            "campaigns_set": {"$addToSet": "$campaign_id"},
            "total_orders": {
                "$sum": {"$cond": [{"$ifNull": ["$order._id", False]}, 1, 0]}
            },
            "verified_payments": {
                "$sum": {"$cond": [{"$eq": ["$order.payment_status", "PAYMENT_VERIFIED"]}, 1, 0]}
            },
            "failed_payments": {
                "$sum": {"$cond": [{"$eq": ["$order.payment_status", "PAYMENT_FAILED"]}, 1, 0]}
            },
            "total_revenue_paise": {
                "$sum": {"$cond": [{"$eq": ["$order.payment_status", "PAYMENT_VERIFIED"]}, "$order.amount", 0]}
            }
        }}
    ]

def get_merchant_historical_performance(merchant_id: str) -> Dict[str, Any]:
    print("DEBUG: type(offers_collection) = ", type(offers_collection))
    pipeline = _build_merchant_analytics_pipeline(merchant_id, group_by_segment=False)
    results = list(offers_collection.aggregate(pipeline))
    
    total_campaigns = campaigns_collection.count_documents({"merchant_id": merchant_id})
    completed_campaigns = campaigns_collection.count_documents({"merchant_id": merchant_id, "status": "COMPLETED"})
    
    if not results:
        return {
            "merchant_id": merchant_id,
            "total_campaigns": total_campaigns,
            "completed_campaigns": completed_campaigns,
            "total_customers": 0,
            "total_offers": 0,
            "total_orders": 0,
            "verified_payments": 0,
            "failed_payments": 0,
            "revenue": 0.0,
            "conversion_rate": 0.0,
            "average_order_value": 0.0
        }
        
    raw = results[0]
    total_customers = len(raw.get("customers_set", []))
    total_offers = len(raw.get("offers_set", []))
    total_orders = raw.get("total_orders", 0)
    verified_payments = raw.get("verified_payments", 0)
    failed_payments = raw.get("failed_payments", 0)
    revenue_inr = raw.get("total_revenue_paise", 0) / 100.0
    
    conversion_rate = 0.0
    if total_offers > 0:
        conversion_rate = (verified_payments / total_offers) * 100.0
        
    average_order_value = 0.0
    if verified_payments > 0:
        average_order_value = revenue_inr / verified_payments
        
    return {
        "merchant_id": merchant_id,
        "total_campaigns": total_campaigns,
        "completed_campaigns": completed_campaigns,
        "total_customers": total_customers,
        "total_offers": total_offers,
        "total_orders": total_orders,
        "verified_payments": verified_payments,
        "failed_payments": failed_payments,
        "revenue": round(revenue_inr, 2),
        "conversion_rate": round(conversion_rate, 2),
        "average_order_value": round(average_order_value, 2)
    }

def get_merchant_segment_performance(merchant_id: str) -> List[Dict[str, Any]]:
    pipeline = _build_merchant_analytics_pipeline(merchant_id, group_by_segment=True)
    results = list(offers_collection.aggregate(pipeline))
    
    formatted = []
    for raw in results:
        segment = raw.get("_id", "unknown")
        total_customers = len(raw.get("customers_set", []))
        total_offers = len(raw.get("offers_set", []))
        total_orders = raw.get("total_orders", 0)
        verified_payments = raw.get("verified_payments", 0)
        failed_payments = raw.get("failed_payments", 0)
        revenue_inr = raw.get("total_revenue_paise", 0) / 100.0
        
        conversion_rate = 0.0
        if total_offers > 0:
            conversion_rate = (verified_payments / total_offers) * 100.0
            
        average_order_value = 0.0
        if verified_payments > 0:
            average_order_value = revenue_inr / verified_payments
            
        formatted.append({
            "segment": segment,
            "total_customers": total_customers,
            "total_offers": total_offers,
            "total_orders": total_orders,
            "verified_payments": verified_payments,
            "failed_payments": failed_payments,
            "revenue": round(revenue_inr, 2),
            "conversion_rate": round(conversion_rate, 2),
            "average_order_value": round(average_order_value, 2)
        })
    return formatted
