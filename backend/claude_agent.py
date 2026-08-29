from openai import OpenAI
import json
from dotenv import load_dotenv
import os
from typing import Dict, Any

load_dotenv()

# Lazy initialization - client created only when needed
client = None

def get_client():
    """Get or create OpenRouter client via OpenAI-compatible API (lazy initialization)"""
    global client
    if client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
        # OpenRouter uses OpenAI-compatible API
        # Create client with minimal configuration to avoid environment issues
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    return client

SYSTEM_PROMPT = """You are an AI revenue optimization agent for a merchant.

Your job is to recommend a campaign offer that is appropriate for the target customer segment while respecting the merchant's business constraints.

If a specific campaign strategy (e.g. 'win-back', 'retention') is provided in the Campaign Context, formulate an offer that actively executes this strategy.

Use the provided customer behavior and campaign goal.

Consider historical learning insights if provided. Do NOT claim "historically this worked" unless the backend supplied historical evidence supporting that statement in the historical context block.

Never exceed the maximum allowed discount.

Never recommend an offer that violates the minimum margin requirement.

Return structured JSON only.

For each segment, respond in JSON ONLY using this schema:
{
  "segment": "...",
  "offer": "...",
  "discount_pct": 0,
  "reason": "...",
  "priority": "low|medium|high"
}
"""

def get_offer_for_segment(
    segment: str, 
    merchant_rules: dict, 
    use_deterministic: bool = False,
    customer_context: dict = None,
    campaign_context: dict = None,
    historical_context: dict = None
) -> dict:
    """
    Call OpenRouter API to get offer for a segment.
    Uses openai/gpt-oss-20b:free (free open-source model via OpenRouter).
    Falls back to deterministic offers if API fails or use_deterministic=True.
    
    Args:
        segment: "loyal", "new_visitor", etc
        merchant_rules: {"max_discount_percentage": 20, ...}
        use_deterministic: If True, use hardcoded offers instead of API
        customer_context: Optional dictionary with actual customer behavioral data
        campaign_context: Optional dictionary with campaign specifics
        historical_context: Optional dictionary with historical performance data
    
    Returns:
        dict with offer details
    """
    
    # Deterministic fallback offers for zero-cost operation
    DETERMINISTIC_OFFERS = {
        "loyal": {
            "recommended_offer_type": "free_shipping",
            "recommended_discount_percentage": 0,
            "reason": "Loyal customers have high lifetime value. Preserve margin with free shipping instead of discount.",
            "confidence": 1.0
        },
        "new_visitor": {
            "recommended_offer_type": "percentage_discount",
            "recommended_discount_percentage": 10,
            "reason": "New visitors need incentive to convert. 10% discount is under max 20% and preserves margin.",
            "confidence": 1.0
        },
        "cart_abandoned": {
            "recommended_offer_type": "flat_discount",
            "recommended_discount_percentage": 5,
            "reason": "Cart abandoned customers are ready to buy. Small coupon recovers lost sale without excessive discount.",
            "confidence": 1.0
        },
        "high_value": {
            "recommended_offer_type": "premium_upgrade",
            "recommended_discount_percentage": 0,
            "reason": "High-value customers don't need discounts. Offer premium products/services to increase order value.",
            "confidence": 1.0
        },
        "price_sensitive": {
            "recommended_offer_type": "percentage_discount",
            "recommended_discount_percentage": 15,
            "reason": "Price-sensitive segment responds to discounts. 15% on bulk purchases increases volume.",
            "confidence": 1.0
        },
        "dormant": {
            "recommended_offer_type": "percentage_discount",
            "recommended_discount_percentage": 20,
            "reason": "Dormant customers need strong incentive to return. Max discount + gift creates urgency.",
            "confidence": 1.0
        },
        "regular": {
            "recommended_offer_type": "loyalty_points",
            "recommended_discount_percentage": 5,
            "reason": "Regular customers are stable. Loyalty program keeps them engaged without high discount.",
            "confidence": 1.0
        }
    }
    
    # Use deterministic offers if requested
    if use_deterministic:
        return DETERMINISTIC_OFFERS.get(segment, DETERMINISTIC_OFFERS["regular"])
    
    # Format historical context appropriately, handling cold start
    historical_summary = "None provided."
    if historical_context:
        overall = historical_context.get("overall", {})
        if overall.get("total_campaigns", 0) == 0:
            historical_summary = "No historical campaign data available yet for this merchant."
        else:
            # We want to provide a compact summary
            segments = historical_context.get("segments", [])
            segment_data = next((s for s in segments if s.get("segment") == segment), None)
            
            summary = {
                "overall_completed_campaigns": overall.get("completed_campaigns", 0),
                "overall_conversion_rate": overall.get("conversion_rate", 0),
            }
            if segment_data:
                summary["segment_conversion_rate"] = segment_data.get("conversion_rate", 0)
                summary["segment_offers_sent"] = segment_data.get("total_offers", 0)
                
            learning = historical_context.get("learning_insights")
            if learning:
                summary["learning_insights"] = {
                    "best_segments": learning.get("best_segments", []),
                    "weak_segments": learning.get("weak_segments", []),
                    "performance_patterns": learning.get("performance_patterns", [])
                }
                
            historical_summary = json.dumps(summary)
            
    user_message = f"""
    Segment: {segment}
    Max discount allowed: {merchant_rules.get('max_discount_percentage', 20)}%
    Min margin required: {merchant_rules.get('min_margin_percentage', 30)}%
    
    Customer Context (Historical Behavior):
    {json.dumps(customer_context) if customer_context else 'None provided.'}
    
    Campaign Context:
    {json.dumps(campaign_context) if campaign_context else 'None provided.'}
    
    Merchant Historical Performance:
    {historical_summary}
    
    What offer should this segment get based on this specific context?
    """
    
    try:
        model_used = "openrouter/free"
        
        # Safe logging implementation
        def redact_sensitive(obj):
            if isinstance(obj, dict):
                return {k: ("***REDACTED***" if any(s in k.lower() for s in ["password", "secret", "key", "uri", "email", "phone", "address", "auth", "token"]) else redact_sensitive(v)) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [redact_sensitive(item) for item in obj]
            return obj

        safe_context = {
            "campaign": redact_sensitive(campaign_context) if campaign_context else "None provided",
            "analytics": "Not used in this request",
            "segment_performance": "Not used in this request",
            "historical_performance": redact_sensitive(historical_context) if historical_context else "None provided",
            "merchant_rules": redact_sensitive(merchant_rules),
            "customer_context": redact_sensitive(customer_context) if customer_context else "None provided",
            "system_prompt": SYSTEM_PROMPT,
            "user_prompt": user_message
        }
        
        print("\n===== OPENROUTER AI CONTEXT =====")
        print(json.dumps(safe_context, indent=4))
        print("===== END OPENROUTER AI CONTEXT =====")
        print(f"Model used: {model_used}\n")
        
        # Try to call OpenRouter API
        openai_client = get_client()
        response = openai_client.chat.completions.create(
            model=model_used,
            max_tokens=500,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ]
        )
        
        response_text = response.choices[0].message.content
        
        # Try to parse JSON
        try:
            offer = json.loads(response_text)
        except:
            # Fallback if not valid JSON
            offer = {
                "segment": segment,
                "offer": "10% Discount",
                "discount_pct": 10,
                "reason": response_text,
                "priority": "medium"
            }
        
        return offer
        
    except Exception as e:
        # If API fails, fall back to deterministic offers
        print(f"[Note] OpenRouter API unavailable ({type(e).__name__}), using deterministic offers")
        return DETERMINISTIC_OFFERS.get(segment, DETERMINISTIC_OFFERS["regular"])


# Test
if __name__ == "__main__":
    merchant_rules = {
        "max_discount_percentage": 20,
        "min_margin_percentage": 30
    }
    
    segments = ["loyal", "new_visitor", "cart_abandoned"]
    
    for segment in segments:
        offer = get_offer_for_segment(segment, merchant_rules)
        print(f"\n{segment.upper()}:")
        print(f"  Offer: {offer.get('offer')}")
        print(f"  Discount: {offer.get('discount_pct')}%")

def generate_campaign_insights(campaign_data: dict, analytics: dict, segments_analytics: list) -> dict:
    """
    Call OpenRouter API to analyze a campaign's performance and provide recommendations.
    
    Returns a structured dictionary:
    {
        "summary": "...",
        "key_insights": ["..."],
        "recommendations": ["..."],
        "segments": [{"segment": "loyal", "observation": "...", "recommendation": "..."}]
    }
    """
    system_prompt = """You are a Campaign Analyst AI.
    
Analyze the provided campaign data and deterministic analytics.
Do not invent any numbers. Only use the metrics provided.

Respond ONLY with a JSON object in this exact structure:
{
    "summary": "1 sentence overview",
    "key_insights": ["insight 1", "insight 2"],
    "recommendations": ["rec 1", "rec 2"],
    "segments": [
        {"segment": "segment_name", "observation": "...", "recommendation": "..."}
    ]
}"""

    context = {
        "campaign": {
            "name": campaign_data.get("campaign_name", "Unknown"),
            "target": campaign_data.get("target_segment", "All"),
            "status": campaign_data.get("status", "Unknown")
        },
        "overall_performance": analytics,
        "segment_performance": segments_analytics
    }
    
    user_message = f"Analyze this campaign:\n{json.dumps(context, indent=2)}"
    
    model_used = "openrouter/free"
    
    # Safe logging implementation
    def redact_sensitive(obj):
        if isinstance(obj, dict):
            return {k: ("***REDACTED***" if any(s in k.lower() for s in ["password", "secret", "key", "uri", "email", "phone", "address", "auth", "token"]) else redact_sensitive(v)) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [redact_sensitive(item) for item in obj]
        return obj

    safe_context = {
        "campaign": redact_sensitive(context.get("campaign", {})),
        "analytics": redact_sensitive(context.get("overall_performance", {})),
        "segment_performance": redact_sensitive(context.get("segment_performance", [])),
        "historical_performance": "Not used in this request",
        "merchant_rules": "Not used in this request",
        "customer_context": "Not used in this request",
        "system_prompt": system_prompt
    }
    
    print("\n===== OPENROUTER AI CONTEXT =====")
    print(json.dumps(safe_context, indent=4))
    print("===== END OPENROUTER AI CONTEXT =====")
    print(f"Model used: {model_used}\n")
    
    try:
        openai_client = get_client()
        response = openai_client.chat.completions.create(
            model=model_used,
            max_tokens=800,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        
        response_text = response.choices[0].message.content
        return json.loads(response_text)
        
    except Exception as e:
        print(f"[Note] Campaign Insights API unavailable: {e}")
        # Return graceful deterministic fallback
        return {
            "summary": f"Campaign {context['campaign']['name']} has {analytics.get('total_offers', 0)} offers and {analytics.get('verified_payments', 0)} verified payments.",
            "key_insights": ["Analytics pulled successfully.", "AI insights currently offline."],
            "recommendations": ["Monitor ongoing performance manually."],
            "segments": [
                {
                    "segment": s.get("segment", "unknown"),
                    "observation": f"{s.get('verified_payments', 0)} conversions",
                    "recommendation": "Maintain strategy."
                } for s in segments_analytics
            ]
        }

def generate_optimization_recommendations(campaign_metrics: dict, segment_metrics: list, historical_performance: dict, merchant_rules: dict, campaign_context: dict) -> dict:
    """
    Call OpenRouter API to generate optimization recommendations for a campaign.
    Returns a structured dictionary of recommendations.
    """
    system_prompt = """You are a Campaign Optimization Agent AI.

Your job is to analyze campaign performance and suggest optimizations to improve future performance.
DO NOT invent metrics. Only rely on the provided data.
You CANNOT recommend:
- discount above merchant max_discount_percentage
- margin below merchant min_margin_percentage
- negative values
- invalid segments

Respond ONLY with a JSON object in this exact structure:
{
    "overall_assessment": "1-2 sentences assessing the campaign",
    "recommendations": [
        {
            "type": "discount_adjustment",
            "segment": "new_visitor",
            "recommended_change": "Increase discount to 15%",
            "reason": "Conversion rate is too low at 5% compared to loyal segment.",
            "priority": "high"
        }
    ]
}

Valid recommendation types:
discount_adjustment, segment_targeting, offer_type_change, campaign_timing, audience_expansion, audience_reduction, campaign_pause
"""

    # Format the context for AI
    context = {
        "merchant_rules": merchant_rules,
        "campaign_context": campaign_context,
        "campaign_metrics": campaign_metrics,
        "segment_metrics": segment_metrics,
        "historical_performance": historical_performance
    }
    
    user_message = f"Please optimize based on the following data:\n{json.dumps(context, indent=2)}"
    
    model_used = "openrouter/free"
    
    def redact_sensitive(obj):
        if isinstance(obj, dict):
            return {k: ("***REDACTED***" if any(s in k.lower() for s in ["password", "secret", "key", "uri", "email", "phone", "address", "auth", "token"]) else redact_sensitive(v)) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [redact_sensitive(item) for item in obj]
        return obj

    safe_context = {
        "campaign": redact_sensitive(campaign_context),
        "analytics": redact_sensitive(campaign_metrics),
        "segment_performance": redact_sensitive(segment_metrics),
        "historical_performance": redact_sensitive(historical_performance),
        "merchant_rules": redact_sensitive(merchant_rules),
        "customer_context": "Not used in this request",
        "system_prompt": system_prompt,
        "user_prompt": user_message
    }
    
    print("\n===== OPENROUTER AI CONTEXT (OPTIMIZATION) =====")
    print(json.dumps(safe_context, indent=4))
    print("===== END OPENROUTER AI CONTEXT (OPTIMIZATION) =====")
    print(f"Model used: {model_used}\n")
    
    try:
        openai_client = get_client()
        response = openai_client.chat.completions.create(
            model=model_used,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        
        response_text = response.choices[0].message.content
        return json.loads(response_text)
        
    except Exception as e:
        print(f"[Note] Optimization API unavailable or failed to parse JSON: {e}")
        # Return fallback recommendation
        return {
            "overall_assessment": "Analysis failed due to API unavailability.",
            "recommendations": []
        }

def generate_feedback_interpretation(before_metrics: Dict[str, Any], after_metrics: Dict[str, Any], changes: Dict[str, Any], outcome: str) -> Dict[str, Any]:
    """Generates an AI interpretation of a campaign's optimization feedback."""
    try:
        client = get_client()

        # Redact sensitive fields if any exist
        def redact_sensitive(obj):
            if isinstance(obj, dict):
                return {k: ("***REDACTED***" if any(s in k.lower() for s in ["password", "secret", "key", "uri", "email", "phone", "address", "auth", "token"]) else redact_sensitive(v)) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [redact_sensitive(item) for item in obj]
            return obj

        safe_before = redact_sensitive(before_metrics)
        safe_after = redact_sensitive(after_metrics)
        safe_changes = redact_sensitive(changes)

        prompt = f"""
You are an expert marketing data analyst evaluating an A/B test or campaign optimization.
The campaign was optimized and allowed to run. We have compared the 'before' metrics to the 'after' metrics.

Before metrics: {json.dumps(safe_before)}
After metrics: {json.dumps(safe_after)}
Changes: {json.dumps(safe_changes)}
Deterministic Outcome: {outcome}

Explain the observed result. Provide an interpretation, a possible explanation, a future recommendation, and a confidence level (low, medium, high) based on data volume.
Ensure your response is valid JSON matching this schema exactly:
{{
    "interpretation": "High-level summary",
    "possible_explanation": "Why it might have happened",
    "future_recommendation": "What to do next",
    "confidence_level": "low|medium|high"
}}
"""

        completion = client.chat.completions.create(
            model="openrouter/free",
            max_tokens=1000,
            messages=[
                {"role": "system", "content": "You analyze campaign data. Reply in strictly structured JSON matching the requested schema. No markdown wrapping."},
                {"role": "user", "content": prompt}
            ]
        )
        
        content = completion.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"[Note] Feedback API unavailable or failed to parse JSON: {e}")
        return {
            "interpretation": "Interpretation unavailable due to API failure.",
            "possible_explanation": "N/A",
            "future_recommendation": "N/A",
            "confidence_level": "low"
        }

def generate_merchant_insights(intelligence_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generates an AI interpretation of a merchant's overall multi-campaign intelligence."""
    try:
        client = get_client()

        # Redact sensitive fields if any exist
        def redact_sensitive(obj):
            if isinstance(obj, dict):
                return {k: ("***REDACTED***" if any(s in k.lower() for s in ["password", "secret", "key", "uri", "email", "phone", "address", "auth", "token"]) else redact_sensitive(v)) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [redact_sensitive(item) for item in obj]
            return obj

        safe_data = redact_sensitive(intelligence_data)

        prompt = f"""
You are an expert marketing strategist analyzing a merchant's overall multi-campaign performance.
Here is the deterministic intelligence data aggregated across all their campaigns, segments, and optimizations:

{json.dumps(safe_data)}

Provide a high-level summary, key findings, strategic opportunities, and warnings.
Ensure your response is valid JSON matching this schema exactly:
{{
    "summary": "High-level summary of merchant performance",
    "key_findings": ["Finding 1", "Finding 2"],
    "opportunities": ["Opportunity 1", "Opportunity 2"],
    "warnings": ["Warning 1"]
}}
"""

        completion = client.chat.completions.create(
            model="openrouter/free",
            max_tokens=1000,
            messages=[
                {"role": "system", "content": "You analyze merchant data. Reply in strictly structured JSON matching the requested schema. No markdown wrapping."},
                {"role": "user", "content": prompt}
            ]
        )
        
        content = completion.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"[Note] Merchant insights API unavailable or failed to parse JSON: {e}")
        return {
            "summary": "Insights unavailable due to API failure.",
            "key_findings": [],
            "opportunities": [],
            "warnings": []
        }

def generate_revenue_recommendation(context: Dict[str, Any]) -> Dict[str, Any]:
    """Generates an AI revenue strategy recommendation based on full merchant context."""
    try:
        client = get_client()

        # Redact sensitive fields if any exist
        def redact_sensitive(obj):
            if isinstance(obj, dict):
                return {k: ("***REDACTED***" if any(s in k.lower() for s in ["password", "secret", "key", "uri", "email", "phone", "address", "auth", "token"]) else redact_sensitive(v)) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [redact_sensitive(item) for item in obj]
            return obj

        safe_context = redact_sensitive(context)

        prompt = f"""
You are the RAZZZ Revenue Agent, an expert AI strategist.
Based on the following complete business context for the merchant, recommend a single, highly actionable campaign strategy to maximize revenue.

Business Context:
{json.dumps(safe_context)}

1. What is the primary business problem or opportunity? (Note: A new campaign with zero data is NOT a failure, it just needs time or testing).
2. Which segment should be prioritized based on the data?
3. What is the recommended strategy and specific action?
4. Why is this action appropriate? (Reasoning must rely on actual metrics and provided historical learning insights. Do NOT invent historical learnings).
5. What evidence supports this?

Ensure your response is valid JSON matching this schema exactly:
{{
    "strategy": "string",
    "recommendation": {{
        "segment": "string (e.g., loyal, new_visitor, cart_abandoned, etc.)",
        "action": "string",
        "offer": "string",
        "discount_percentage": number
    }},
    "reasoning": "string",
    "priority": "high|medium|low",
    "confidence": "high|medium|low",
    "evidence": ["string1", "string2"],
    "limitations": ["string1"]
}}
"""

        completion = client.chat.completions.create(
            model="openrouter/free",
            max_tokens=1000,
            messages=[
                {"role": "system", "content": "You are a revenue strategy agent. Reply in strictly structured JSON matching the requested schema. No markdown wrapping."},
                {"role": "user", "content": prompt}
            ]
        )
        
        content = completion.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"[Note] Revenue recommendation API unavailable or failed to parse JSON: {e}")
        return {
            "strategy": "Wait for API recovery",
            "recommendation": {
                "segment": "unknown",
                "action": "API failure fallback",
                "offer": "10% Discount",
                "discount_percentage": 10
            },
            "reasoning": "OpenRouter API is currently unavailable.",
            "priority": "low",
            "confidence": "low",
            "evidence": [],
            "limitations": ["AI processing offline"]
        }

def determine_campaign_strategy(goal: str, merchant_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes the merchant's goal and context to identify the best business opportunity
    and formulate a high-level campaign strategy.
    """
    try:
        client = get_client()

        def redact_sensitive(obj):
            if isinstance(obj, dict):
                return {k: ("***REDACTED***" if any(s in k.lower() for s in ["password", "secret", "key", "uri", "email", "phone", "address", "auth", "token"]) else redact_sensitive(v)) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [redact_sensitive(item) for item in obj]
            return obj

        safe_context = redact_sensitive(merchant_context)

        prompt = f"""
You are the RAZZZ AI Campaign Strategist.
The merchant has requested a new campaign with the following goal: "{goal}"

Here is the complete business context (customer segments, sizes, metrics, historical insights, merchant rules):
{json.dumps(safe_context)}

Your job is to act as a revenue strategist, NOT just an offer generator.
Analyze the provided goal against the actual data. Detect the most meaningful opportunity (e.g., if the goal is 'increase sales', and you see dormant customers have a very low conversion rate, the opportunity is reactivation).

Formulate a Campaign Strategy (e.g., acquisition, win-back, retention, cart recovery, high-value upsell, margin protection).
Select the most relevant target segments from the available segments in the data. You can select one, multiple, or none if irrelevant. Do not just automatically select 'loyal', 'new_visitor', and 'dormant' unless justified.

You MUST enforce merchant rules (max discount, min margin) in your recommendations.
You MUST base your reasoning ONLY on the provided data. Do not invent metrics or claim historical causation without evidence.

Respond ONLY with a valid JSON object matching this exact schema:
{{
  "business_goal": "The merchant's stated goal",
  "opportunity": {{
    "title": "Short title of the opportunity",
    "description": "Explanation of the opportunity based on data",
    "evidence": ["Data point 1", "Data point 2"]
  }},
  "strategy": {{
    "type": "Strategy type (e.g., win-back, retention)",
    "name": "Human readable strategy name",
    "description": "How this strategy works"
  }},
  "target_segments": ["segment_name1", "segment_name2"],
  "recommended_action": "High level action to take",
  "confidence": "high|medium|low",
  "evidence": ["Why this strategy will work"],
  "limitations": ["Any risks or data limitations"]
}}
"""

        completion = client.chat.completions.create(
            model="openrouter/free",
            max_tokens=1500,
            messages=[
                {"role": "system", "content": "You are a campaign strategy agent. Reply strictly in JSON matching the requested schema. No markdown wrapping."},
                {"role": "user", "content": prompt}
            ]
        )
        
        content = completion.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"[Note] Strategy API unavailable or failed to parse JSON: {e}")
        # Safe fallback
        return {
            "business_goal": goal,
            "opportunity": {
                "title": "Fallback Strategy",
                "description": "API unavailable, using default opportunity.",
                "evidence": []
            },
            "strategy": {
                "type": "general",
                "name": "Standard Engagement",
                "description": "Standard engagement campaign."
            },
            "target_segments": ["loyal", "new_visitor", "dormant"],
            "recommended_action": "Proceed with default offers.",
            "confidence": "low",
            "evidence": [],
            "limitations": ["AI Strategy generation offline"]
        }