import sys
from pydantic import BaseModel, Field, ValidationError
from segmentation import segment_customer
import claude_agent
from guardrails import validate_offer
from analytics import get_merchant_historical_performance, get_merchant_segment_performance
from historical_analyzer import get_historical_learning_insights

from typing import Optional

class AIRecommendationSchema(BaseModel):
    campaign_goal: Optional[str] = None
    target_segment: Optional[str] = None
    why_this_segment: Optional[str] = None
    recommended_strategy: Optional[str] = None
    offer: Optional[str] = None
    why_this_offer: Optional[str] = None
    discount_if_applicable: Optional[float] = None
    duration: Optional[str] = None
    ai_reasoning: Optional[str] = None
    merchant_constraints: Optional[str] = None
    expected_objective: Optional[str] = None
    recommended_discount_percentage: Optional[float] = None
    recommended_offer_type: Optional[str] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None

def run_offer_decision_engine(
    merchant_id: str,
    segment: str = None,
    segment_stats: dict = None,
    merchant_rules: dict = None,
    campaign_context: dict = None,
    customer: dict = None
) -> dict:
    """
    AI OFFER DECISION ENGINE
    Pipeline:
    1. CURRENT SEGMENT + SEGMENT STATS
    2. MERCHANT RULES
    3. CURRENT CAMPAIGN + CURRENT CAMPAIGN PERFORMANCE (via campaign_context)
    4. HISTORICAL MERCHANT PERFORMANCE + HISTORICAL SEGMENT PERFORMANCE
    5. AI -> OFFER STRATEGY RECOMMENDATION
    6. DETERMINISTIC GUARDRAILS -> FINAL APPROVED OFFER
    """
    
    if customer is not None:
        segment = segment_customer(customer)
        # Fake stats for individual customer generation flow
        segment_stats = {"average_purchase_count": customer.get("purchase_count", 0)}
    elif segment is None or segment_stats is None:
        raise ValueError("Either customer or (segment and segment_stats) must be provided")

    if not merchant_rules or "max_discount_percentage" not in merchant_rules:
        raise ValueError("Merchant guardrail rules are not present. Complete your merchant settings before generating campaigns.")

    # 2. Collect Historical Performance
    historical_context = {
        "overall": get_merchant_historical_performance(merchant_id),
        "segments": get_merchant_segment_performance(merchant_id),
        "learning_insights": get_historical_learning_insights(merchant_id)
    }
    
    # 3. AI Offer Strategy Recommendation
    try:
        ai_offer = claude_agent.get_offer_for_segment(
            segment,
            merchant_rules,
            use_deterministic=False,
            customer_context=customer if customer is not None else segment_stats,
            campaign_context=campaign_context,
            historical_context=historical_context
        )
        if not isinstance(ai_offer, dict):
            raise ValueError("Invalid response from AI: Not a dictionary")
        
        # Pydantic validation
        try:
            AIRecommendationSchema(**ai_offer)
        except ValidationError as ve:
            raise ValueError(f"Invalid response from AI: {ve}")
    except Exception as e:
        print(f"[Decision Engine] AI generation failed: {e}")
        # Let caller handle the exception (like FastAPI 500 error)
        raise e
    
    # Map the new schema to the old format expected by guardrails and callers if we fallback
    offer_for_guardrails = ai_offer.copy()
    if "discount_if_applicable" in offer_for_guardrails and offer_for_guardrails.get("discount_pct") is None:
        offer_for_guardrails["discount_pct"] = offer_for_guardrails["discount_if_applicable"]
    elif "recommended_discount_percentage" in offer_for_guardrails and offer_for_guardrails.get("discount_pct") is None:
        offer_for_guardrails["discount_pct"] = offer_for_guardrails["recommended_discount_percentage"]
    
    # Create mock customer for guardrails (expects purchase_count)
    guardrail_customer = {"purchase_count": segment_stats.get("average_purchase_count", 0)}
    
    # 4. Deterministic Guardrails Validation
    is_valid = validate_offer(offer_for_guardrails, merchant_rules, guardrail_customer)
    
    if not is_valid:
        print(f"[Decision Engine] Guardrails blocked AI offer. Falling back to deterministic safe offer.")
        ai_offer = claude_agent.get_offer_for_segment(segment, merchant_rules, use_deterministic=True, campaign_context=campaign_context)
        offer_for_guardrails = ai_offer.copy()
        if "discount_if_applicable" in offer_for_guardrails and offer_for_guardrails.get("discount_pct") is None:
            offer_for_guardrails["discount_pct"] = offer_for_guardrails["discount_if_applicable"]
            
        if not validate_offer(offer_for_guardrails, merchant_rules, guardrail_customer):
            raise ValueError("Guardrails blocked even deterministic fallback offer")
            
    # 5. Final Approved Offer
    final_offer_details = ai_offer.get("offer", "")
    final_discount = ai_offer.get("discount_if_applicable", ai_offer.get("discount_pct", 0))
    final_explanation = ai_offer.get("ai_reasoning", ai_offer.get("why_this_offer", ""))
    
    return {
        "segment": segment,
        "offer_details": final_offer_details,
        "discount_percentage": float(final_discount if final_discount is not None else 0),
        "explanation": final_explanation,
        "campaign_goal": ai_offer.get("campaign_goal"),
        "why_this_segment": ai_offer.get("why_this_segment"),
        "recommended_strategy": ai_offer.get("recommended_strategy"),
        "why_this_offer": ai_offer.get("why_this_offer"),
        "duration": ai_offer.get("duration"),
        "merchant_constraints": ai_offer.get("merchant_constraints"),
        "expected_objective": ai_offer.get("expected_objective")
    }

def recommend_offer_strategy(
    merchant_id: str,
    customer: dict,
    merchant_rules: dict,
    campaign_context: dict = None,
    campaign_id: str = None
) -> dict:
    """
    Recommends an offer strategy and evaluates it against guardrails without automatic fallback.
    Returns the exact recommendation format required for the /offers/recommend endpoint.
    """
    segment = segment_customer(customer)
    
    historical_context = {
        "overall": get_merchant_historical_performance(merchant_id),
        "segments": get_merchant_segment_performance(merchant_id),
        "learning_insights": get_historical_learning_insights(merchant_id)
    }
    
    guardrail_status = "APPROVED"
    ai_offer = None
    
    try:
        ai_offer = claude_agent.get_offer_for_segment(
            segment,
            merchant_rules,
            use_deterministic=False,
            customer_context=customer,
            campaign_context=campaign_context,
            historical_context=historical_context
        )
        
        # Validation of AI Output structure using Pydantic
        if not isinstance(ai_offer, dict):
            guardrail_status = "ERROR_MALFORMED_JSON"
        else:
            try:
                validated_offer = AIRecommendationSchema(**ai_offer)
                
                # Unsupported offer type validation
                valid_types = ["percentage_discount", "flat_discount", "free_shipping", "premium_upgrade", "loyalty_points"]
                
                if validated_offer.recommended_discount_percentage is None:
                    guardrail_status = "ERROR_MISSING_DISCOUNT"
                elif validated_offer.confidence is None or validated_offer.confidence > 1.0 or validated_offer.confidence < 0.0:
                    guardrail_status = "ERROR_INVALID_CONFIDENCE"
                elif validated_offer.recommended_offer_type not in valid_types:
                    guardrail_status = "ERROR_UNSUPPORTED_OFFER_TYPE"
                elif validated_offer.recommended_discount_percentage < 0:
                    guardrail_status = "ERROR_NEGATIVE_DISCOUNT"
                    
            except ValidationError as ve:
                # Map specific pydantic errors to our custom statuses
                err_str = str(ve).lower()
                if "recommended_discount_percentage" in err_str:
                    if "missing" in err_str:
                        guardrail_status = "ERROR_MISSING_DISCOUNT"
                    else:
                        guardrail_status = "ERROR_MALFORMED_DISCOUNT"
                elif "confidence" in err_str:
                    guardrail_status = "ERROR_INVALID_CONFIDENCE"
                else:
                    guardrail_status = "ERROR_MALFORMED_JSON"
                    
    except Exception as e:
        print(f"[Decision Engine] OpenRouter failure: {e}")
        guardrail_status = "ERROR_AI_FAILURE"
        ai_offer = {}
        
    # Guardrails validation
    if guardrail_status == "APPROVED":
        offer_for_guardrails = ai_offer.copy()
        if "recommended_discount_percentage" in offer_for_guardrails:
            offer_for_guardrails["discount_pct"] = offer_for_guardrails["recommended_discount_percentage"]
            
        is_valid = validate_offer(offer_for_guardrails, merchant_rules, customer)
        if not is_valid:
            guardrail_status = "REJECTED_BY_GUARDRAILS"
            
    # Normalize missing fields for the response if failed
    if not isinstance(ai_offer, dict):
        ai_offer = {}
        
    recommended_discount = ai_offer.get("recommended_discount_percentage")
    try:
        recommended_discount = float(recommended_discount)
    except (ValueError, TypeError):
        recommended_discount = 0.0
        
    confidence = ai_offer.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except (ValueError, TypeError):
        confidence = 0.0
        
    return {
        "customer_id": customer.get("id", customer.get("customer_id")),
        "campaign_id": campaign_id,
        "segment": segment,
        "recommended_offer_type": ai_offer.get("recommended_offer_type", "unknown"),
        "recommended_discount_percentage": recommended_discount,
        "reason": ai_offer.get("reason", "AI recommendation failed or was rejected."),
        "confidence": confidence,
        "guardrail_status": guardrail_status
    }

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    print("=" * 60)
    print("AI OFFER DECISION ENGINE DEMO")
    print("=" * 60)
    
    merchant_rules = {
        "max_discount_percentage": 20.0,
        "min_margin_percentage": 30.0
    }
    
    test_customer = {
        "id": "cust_123",
        "purchase_count": 0,
        "cart_status": "browsing"
    }
    
    try:
        result = run_offer_decision_engine(
            merchant_id="demo_merchant",
            customer=test_customer,
            merchant_rules=merchant_rules
        )
        print("Final Approved Offer:")
        for k, v in result.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"Error: {e}")
