from openai import OpenAI
import json
from dotenv import load_dotenv
import os
from typing import Dict, Any

def parse_json_safely(text: str) -> Any:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    try:
        return json.loads(text)
    except Exception as e:
        print(f"JSON parsing error: {e}")
        import re
        # Attempt to extract JSON from surrounding conversational text
        match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        return {}

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
            base_url="https://openrouter.ai/api/v1",
            timeout=15.0
        )
    return client

SYSTEM_PROMPT = """You are an AI Campaign Intelligence Engine for a merchant.

Your job is to read the campaign goal, merchant constraints, and actual customer data, and dynamically group customers into meaningful segments.
Do not force customers into predefined buckets unless the data and goal support it. 
You can create segments like "High-Value Cart Abandoners", "Price-Sensitive Recent Buyers", "VIP Summer Shoppers", etc.
Only create a segment if there are actual customers that fit the criteria.
Assign the exact customer IDs to the segments they belong to. A customer can only belong to one segment.
Every segment MUST respect the merchant rules (e.g. max_discount_percentage, min_margin_percentage).
If a segment does not warrant an offer or discount, provide 0 discount.

Respond strictly with valid JSON matching this schema exactly:
{
  "segments": [
    {
      "segment": "Name of the dynamic segment",
      "segment_description": "Why these customers were grouped together based on their data",
      "customer_ids": ["cust_001", "cust_002"],
      "strategy": "The strategic approach (e.g., win-back, retention)",
      "offer": "The specific offer/incentive wording",
      "discount_pct": 0,
      "duration_days": 7,
      "reasoning": "Why this specific offer works for this segment",
      "data_evidence": ["Evidence 1 from data", "Evidence 2 from data"],
      "merchant_constraints": ["Rule 1 applied"],
      "expected_objective": "What is the expected outcome",
      "confidence": "high|medium|low"
    }
  ]
}
"""

def generate_dynamic_fallback(customers: list, merchant_rules: dict, goal: str) -> dict:
    """Generates a dynamic fallback clustering if AI is offline."""
    goal_lower = goal.lower()
    
    is_acquisition = 'acquire' in goal_lower or 'new' in goal_lower
    is_winback = 'win' in goal_lower or 'dormant' in goal_lower or 're-engage' in goal_lower
    is_retention = 'summer' in goal_lower or 'promote' in goal_lower
    
    segments = []
    
    # Simple deterministic clustering based on goal
    if is_winback:
        dormant_ids = [c["id"] for c in customers if c.get("days_since_last_purchase", 0) > 60]
        if dormant_ids:
            segments.append({
                "segment": "Dormant Customers",
                "segment_description": "Customers who haven't purchased in >60 days",
                "customer_ids": dormant_ids,
                "strategy": "Win-back / Reactivation",
                "offer": f"{min(25, merchant_rules.get('max_discount_percentage', 20))}% off to return",
                "discount_pct": min(25, merchant_rules.get("max_discount_percentage", 20)),
                "duration_days": 7,
                "reasoning": "High discount to break dormancy",
                "data_evidence": [f"{len(dormant_ids)} customers found with >60 days since last purchase"],
                "merchant_constraints": [f"Max discount {merchant_rules.get('max_discount_percentage', 20)}%"],
                "expected_objective": "Reactivation",
                "confidence": "medium"
            })
            
    elif is_acquisition:
        new_ids = [c["id"] for c in customers if c.get("purchase_count", 0) == 0]
        if new_ids:
            segments.append({
                "segment": "New Prospects",
                "segment_description": "Customers with 0 previous purchases",
                "customer_ids": new_ids,
                "strategy": "First-time Conversion",
                "offer": f"{min(20, merchant_rules.get('max_discount_percentage', 20))}% off first purchase",
                "discount_pct": min(20, merchant_rules.get("max_discount_percentage", 20)),
                "duration_days": 3,
                "reasoning": "Strong incentive for first purchase",
                "data_evidence": [f"{len(new_ids)} customers with 0 purchases"],
                "merchant_constraints": [f"Max discount {merchant_rules.get('max_discount_percentage', 20)}%"],
                "expected_objective": "First Purchase",
                "confidence": "high"
            })
            
    else:
        # Default retention / engagement
        loyal_ids = [c["id"] for c in customers if c.get("purchase_count", 0) >= 3]
        if loyal_ids:
            segments.append({
                "segment": "Loyal Shoppers",
                "segment_description": "Customers with >=3 purchases",
                "customer_ids": loyal_ids,
                "strategy": "VIP Retention",
                "offer": "Early Access & VIP Treatment",
                "discount_pct": 0,
                "duration_days": 14,
                "reasoning": "Reward loyalty with access, preserving margins",
                "data_evidence": [f"{len(loyal_ids)} customers with >=3 purchases"],
                "merchant_constraints": ["Margin preservation for frequent buyers"],
                "expected_objective": "Increase LTV",
                "confidence": "high"
            })
            
    # Catch-all for unassigned customers
    assigned = set()
    for s in segments:
        assigned.update(s["customer_ids"])
    
    remaining_ids = [c["id"] for c in customers if c["id"] not in assigned]
    if remaining_ids:
        segments.append({
            "segment": "General Audience",
            "segment_description": "Remaining active customers",
            "customer_ids": remaining_ids,
            "strategy": "Standard Engagement",
            "offer": f"{min(10, merchant_rules.get('max_discount_percentage', 10))}% off next order",
            "discount_pct": min(10, merchant_rules.get("max_discount_percentage", 10)),
            "duration_days": 7,
            "reasoning": "Broad incentive for general engagement",
            "data_evidence": [f"{len(remaining_ids)} remaining customers"],
            "merchant_constraints": [f"Max discount {merchant_rules.get('max_discount_percentage', 10)}%"],
            "expected_objective": "Incremental Sales",
            "confidence": "low"
        })
        
    return {"segments": segments}


def generate_campaign_intelligence(
    goal: str,
    customers: list,
    merchant_rules: dict,
    historical_context: dict = None,
    use_deterministic: bool = False
) -> dict:
    """
    Call OpenRouter API to analyze all customers, group them into data-driven segments,
    and generate tailored offers based on the campaign goal.
    """
    if use_deterministic or not customers:
        return generate_dynamic_fallback(customers, merchant_rules, goal)
        
    # Anonymize/minify customer data to save tokens
    minified_customers = []
    for c in customers:
        minified_customers.append({
            "id": c.get("id"),
            "purchase_count": c.get("purchase_count", 0),
            "days_since_last_purchase": c.get("days_since_last_purchase", 999),
            "lifetime_value": c.get("lifetime_value", 0),
            "cart_status": c.get("cart_status", "browsing"),
            "average_order_value": c.get("average_order_value", 0)
        })
        
    user_message = f"""
    Campaign Goal: {goal}
    
    Merchant Guardrail Constraints (HARD CONSTRAINTS - NEVER VIOLATE):
    - Maximum discount allowed: {merchant_rules.get('max_discount_percentage', 20)}% (Never recommend higher)
    - Minimum order value: {merchant_rules.get('min_order_value', 0)}
    - Free shipping allowed: {merchant_rules.get('free_shipping_allowed', True)}
    - High-value customer protection: {merchant_rules.get('high_value_customer_protection', False)} (If true, prefer non-discount or VIP incentives over high discounts for high-value customers)
    - Maximum campaign budget: {merchant_rules.get('max_campaign_budget', 'Not set')}
    - Minimum margin required: {merchant_rules.get('min_margin_percentage', 25)}%
    
    Customer Dataset:
    {json.dumps(minified_customers)}
    
    Based on the goal and dataset, group the customers into dynamic segments and recommend an offer for each adhering strictly to the merchant guardrail constraints.
    """
    
    try:
        model_used = "openrouter/free"
        
        safe_context = {
            "campaign_goal": goal,
            "merchant_rules": merchant_rules,
            "customer_count": len(minified_customers),
            "system_prompt": SYSTEM_PROMPT
        }
        
        print("\n===== OPENROUTER AI CONTEXT =====")
        print(json.dumps(safe_context, indent=4))
        print("===== END OPENROUTER AI CONTEXT =====")
        print(f"Model used: {model_used}\n")
        
        openai_client = get_client()
        response = openai_client.chat.completions.create(
            model=model_used,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ]
        )
        
        response_text = response.choices[0].message.content
        
        try:
            intelligence = parse_json_safely(response_text)
            if "segments" not in intelligence:
                raise ValueError("Missing 'segments' key in AI response")
            return intelligence
        except Exception as e:
            print(f"[Note] Failed to parse AI JSON ({e}), using fallback")
            return generate_dynamic_fallback(customers, merchant_rules, goal)
            
    except Exception as e:
        print(f"[Note] OpenRouter API unavailable ({type(e).__name__}), using fallback")
        return generate_dynamic_fallback(customers, merchant_rules, goal)


def get_offer_for_segment(
    segment: str, 
    merchant_rules: dict, 
    use_deterministic: bool = False,
    customer_context: dict = None,
    campaign_context: dict = None,
    historical_context: dict = None
) -> dict:
    """
    Call OpenRouter API or use deterministic fallback to get an offer recommendation for a segment.
    Strictly adheres to merchant guardrails.
    """
    max_discount = float(merchant_rules.get("max_discount_percentage", 20.0)) if merchant_rules else 20.0

    DETERMINISTIC_OFFERS = {
        "loyal": {
            "recommended_offer_type": "free_shipping",
            "recommended_discount_percentage": 0,
            "reason": "Loyal customers have high lifetime value. Preserve margin with VIP perks instead of discount.",
            "confidence": 1.0,
            "campaign_goal": "Retention",
            "why_this_segment": "High-value loyal purchasers",
            "recommended_strategy": "VIP Retention",
            "offer": "VIP Free Shipping and Early Access",
            "why_this_offer": "Preserve margins while rewarding customer loyalty",
            "discount_if_applicable": 0
        },
        "new_visitor": {
            "recommended_offer_type": "percentage_discount",
            "recommended_discount_percentage": min(10.0, max_discount),
            "reason": f"New visitors need an incentive to convert. {min(10.0, max_discount)}% discount converts without violating guardrails.",
            "confidence": 1.0,
            "campaign_goal": "First-time Conversion",
            "why_this_segment": "Browsers with zero prior purchases",
            "recommended_strategy": "First-time Conversion",
            "offer": f"{int(min(10.0, max_discount))}% off first order",
            "why_this_offer": "Incentivize initial checkout",
            "discount_if_applicable": min(10.0, max_discount)
        },
        "cart_abandoned": {
            "recommended_offer_type": "percentage_discount",
            "recommended_discount_percentage": min(15.0, max_discount),
            "reason": f"Cart abandoners have high purchase intent. {min(15.0, max_discount)}% discount recovers abandoned cart safely.",
            "confidence": 1.0,
            "campaign_goal": "Cart Recovery",
            "why_this_segment": "Shoppers with active abandoned carts",
            "recommended_strategy": "Cart Recovery",
            "offer": f"{int(min(15.0, max_discount))}% off to complete order",
            "why_this_offer": "Urgency and incentive to finish purchase",
            "discount_if_applicable": min(15.0, max_discount)
        },
        "dormant": {
            "recommended_offer_type": "percentage_discount",
            "recommended_discount_percentage": min(20.0, max_discount),
            "reason": f"Dormant customers require a stronger reactivation offer capped at merchant max discount ({max_discount}%).",
            "confidence": 1.0,
            "campaign_goal": "Reactivation",
            "why_this_segment": "Customers with no orders in over 60 days",
            "recommended_strategy": "Win-back",
            "offer": f"{int(min(20.0, max_discount))}% off welcome back",
            "why_this_offer": "Win-back incentive",
            "discount_if_applicable": min(20.0, max_discount)
        },
        "regular": {
            "recommended_offer_type": "loyalty_points",
            "recommended_discount_percentage": min(5.0, max_discount),
            "reason": "Regular customers are steady. Small reward preserves profitability.",
            "confidence": 1.0,
            "campaign_goal": "Repeat Purchase",
            "why_this_segment": "Consistent periodic buyers",
            "recommended_strategy": "Engagement",
            "offer": f"{int(min(5.0, max_discount))}% off next order",
            "why_this_offer": "Consistent engagement incentive",
            "discount_if_applicable": min(5.0, max_discount)
        }
    }

    if use_deterministic:
        return DETERMINISTIC_OFFERS.get(segment, DETERMINISTIC_OFFERS["regular"])

    prompt = f"""
    Segment: {segment}
    Merchant Constraints (HARD RULES):
    - Max discount: {max_discount}%
    - Min order value: {merchant_rules.get('min_order_value', 0)}
    - Free shipping allowed: {merchant_rules.get('free_shipping_allowed', True)}
    - High-value customer protection: {merchant_rules.get('high_value_customer_protection', False)}
    
    Customer Context: {json.dumps(customer_context) if customer_context else 'None'}
    Campaign Context: {json.dumps(campaign_context) if campaign_context else 'None'}
    
    Recommend the optimal offer adhering strictly to merchant constraints. Return JSON matching:
    {{
      "recommended_offer_type": "string",
      "recommended_discount_percentage": {min(10.0, max_discount)},
      "reason": "string",
      "confidence": 0.9,
      "campaign_goal": "string",
      "why_this_segment": "string",
      "recommended_strategy": "string",
      "offer": "string",
      "why_this_offer": "string",
      "discount_if_applicable": {min(10.0, max_discount)}
    }}
    """

    try:
        openai_client = get_client()
        response = openai_client.chat.completions.create(
            model="openrouter/free",
            max_tokens=600,
            messages=[
                {"role": "system", "content": "You recommend offers adhering strictly to merchant guardrail rules. Reply strictly in JSON."},
                {"role": "user", "content": prompt}
            ]
        )
        data = parse_json_safely(response.choices[0].message.content)
        if not isinstance(data, dict) or not data:
            return DETERMINISTIC_OFFERS.get(segment, DETERMINISTIC_OFFERS["regular"])
        return data
    except Exception as e:
        print(f"[Note] get_offer_for_segment API call failed ({e}), using deterministic offer")
        return DETERMINISTIC_OFFERS.get(segment, DETERMINISTIC_OFFERS["regular"])


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
        return parse_json_safely(response_text)
        
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
        return parse_json_safely(response_text)
        
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
        return parse_json_safely(content)
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
        return parse_json_safely(content)
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
        return parse_json_safely(content)
    except Exception as e:
        print(f"[Note] Revenue recommendation API unavailable or failed to parse JSON: {e}")
        
        target_segment = "cart_abandoned"
        try:
            segments = context.get("segment_counts", {})
            if segments:
                target_segment = max(segments, key=segments.get)
        except:
            pass

        max_allowed_discount = float(context.get("merchant_rules", {}).get("max_discount_percentage", 20.0))
        safe_fallback_discount = min(10.0, max_allowed_discount)
        safe_display_discount = int(safe_fallback_discount) if safe_fallback_discount.is_integer() else safe_fallback_discount

        return {
            "strategy": "Re-engage High Value Segments",
            "recommendation": {
                "segment": target_segment,
                "action": "Targeted Discount",
                "offer": f"{safe_display_discount}% off for {target_segment} customers",
                "discount_percentage": safe_fallback_discount
            },
            "reasoning": f"Focusing on the {target_segment} segment offers a strong opportunity for conversion based on current data. (Deterministic Fallback used due to AI unavailability).",
            "priority": "high",
            "confidence": "medium",
            "evidence": [f"{target_segment} is a key segment for the merchant"],
            "limitations": ["Fallback strategy used due to AI API unavailability"]
        }

