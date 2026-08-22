from anthropic import Anthropic
import json
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

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

def get_offer_for_segment(segment: str, merchant_rules: dict) -> dict:
    """
    Call Claude API to get offer for a segment.
    
    Args:
        segment: "loyal", "new_visitor", etc
        merchant_rules: {"max_discount_percentage": 20, ...}
    
    Returns:
        dict with offer details
    """
    
    user_message = f"""
    Segment: {segment}
    Max discount allowed: {merchant_rules.get('max_discount_percentage', 20)}%
    Min margin required: {merchant_rules.get('min_margin_percentage', 30)}%
    
    What offer should this segment get?
    """
    
    # Call Claude
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )
    
    response_text = response.content[0].text
    
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