from openai import OpenAI
import json
from dotenv import load_dotenv
import os

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

SYSTEM_PROMPT = """You are an AI Revenue Growth Agent.

Your job: Decide what offer each customer segment should get.

RULES:
1. Max discount = 20%
2. Min margin = 30%
3. Loyal customers: NO discount (preserve margin)
4. New visitors: 10% off (acquire customer)
5. Cart abandoned: ₹200 coupon (recovery)
6. High value: Premium bundle (upsell)

For each segment, respond in JSON ONLY:
{"segment": "segment_name", "offer": "10% off", "discount_pct": 10, "reasoning": "why"}

Be smart. Don't waste money on loyal customers.
"""

def get_offer_for_segment(segment: str, merchant_rules: dict, use_deterministic: bool = False) -> dict:
    """
    Call OpenRouter API to get offer for a segment.
    Uses openai/gpt-oss-20b:free (free open-source model via OpenRouter).
    Falls back to deterministic offers if API fails or use_deterministic=True.
    
    Args:
        segment: "loyal", "new_visitor", etc
        merchant_rules: {"max_discount_percentage": 20, ...}
        use_deterministic: If True, use hardcoded offers instead of API
    
    Returns:
        dict with offer details
    """
    
    # Deterministic fallback offers for zero-cost operation
    DETERMINISTIC_OFFERS = {
        "loyal": {
            "segment": "loyal",
            "offer": "Free shipping on next purchase",
            "discount_pct": 0,
            "reasoning": "Loyal customers have high lifetime value. Preserve margin with free shipping instead of discount."
        },
        "new_visitor": {
            "segment": "new_visitor",
            "offer": "10% off first purchase",
            "discount_pct": 10,
            "reasoning": "New visitors need incentive to convert. 10% discount is under max 20% and preserves margin."
        },
        "cart_abandoned": {
            "segment": "cart_abandoned",
            "offer": "₹200 instant coupon to recover cart",
            "discount_pct": 5,
            "reasoning": "Cart abandoned customers are ready to buy. Small coupon recovers lost sale without excessive discount."
        },
        "high_value": {
            "segment": "high_value",
            "offer": "Premium bundle upgrade at no extra cost",
            "discount_pct": 0,
            "reasoning": "High-value customers don't need discounts. Offer premium products/services to increase order value."
        },
        "price_sensitive": {
            "segment": "price_sensitive",
            "offer": "15% bulk purchase discount",
            "discount_pct": 15,
            "reasoning": "Price-sensitive segment responds to discounts. 15% on bulk purchases increases volume."
        },
        "dormant": {
            "segment": "dormant",
            "offer": "20% off to re-engage + free gift",
            "discount_pct": 20,
            "reasoning": "Dormant customers need strong incentive to return. Max discount + gift creates urgency."
        },
        "regular": {
            "segment": "regular",
            "offer": "5% loyalty points on next purchase",
            "discount_pct": 5,
            "reasoning": "Regular customers are stable. Loyalty program keeps them engaged without high discount."
        }
    }
    
    # Use deterministic offers if requested
    if use_deterministic:
        return DETERMINISTIC_OFFERS.get(segment, DETERMINISTIC_OFFERS["regular"])
    
    user_message = f"""
    Segment: {segment}
    Max discount allowed: {merchant_rules.get('max_discount_percentage', 20)}%
    Min margin required: {merchant_rules.get('min_margin_percentage', 30)}%
    
    What offer should this segment get?
    """
    
    try:
        # Try to call OpenRouter API
        openai_client = get_client()
        response = openai_client.chat.completions.create(
            model="openrouter/free",
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
                "offer": "Check offer manually",
                "discount_pct": 10,
                "reasoning": response_text
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