import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

class TestAIIntelligence(unittest.TestCase):

    def setUp(self):
        self.patcher_campaigns = patch('main.campaigns_collection')
        self.mock_campaigns = self.patcher_campaigns.start()
        
        self.patcher_merchants = patch('main.merchants_collection')
        self.mock_merchants = self.patcher_merchants.start()
        
        self.patcher_offers = patch('main.offers_collection')
        self.mock_offers = self.patcher_offers.start()

    def tearDown(self):
        self.patcher_campaigns.stop()
        self.patcher_merchants.stop()
        self.patcher_offers.stop()

    @patch('claude_agent.get_offer_for_segment')
    @patch('guardrails.validate_offer')
    def test_offer_generation_captures_explanation(self, mock_validate, mock_get_offer):
        """Test POST /offers/generate correctly passes context and stores explanation."""
        self.mock_merchants.find_one.return_value = {"merchant_id": "merch_1"}
        mock_get_offer.return_value = {
            "segment": "loyal",
            "offer": "Free shipping",
            "discount_pct": 0,
            "reasoning": "Loyal customers get free shipping."
        }
        mock_validate.return_value = True
        
        response = client.post("/offers/generate", json={
            "merchant_id": "merch_1",
            "customer": {
                "id": "c1",
                "purchase_count": 5
            }
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["explanation"], "Loyal customers get free shipping.")
        
        # Verify it was passed properly to the AI
        mock_get_offer.assert_called_once()
        kwargs = mock_get_offer.call_args.kwargs
        self.assertEqual(kwargs.get("customer_context", {}).get("id"), "c1")

    @patch('analytics.get_campaign_analytics')
    @patch('analytics.get_campaign_segment_analytics')
    @patch('claude_agent.generate_campaign_insights')
    def test_campaign_insights_endpoint(self, mock_generate_insights, mock_get_segments, mock_get_analytics):
        self.mock_campaigns.find_one.return_value = {"campaign_id": "camp1"}
        mock_get_analytics.return_value = {"total_offers": 100}
        mock_get_segments.return_value = [{"segment": "loyal", "verified_payments": 10}]
        
        mock_generate_insights.return_value = {
            "summary": "Solid campaign.",
            "key_insights": ["Insight 1"],
            "recommendations": ["Do x"],
            "segments": [{"segment": "loyal", "observation": "Great", "recommendation": "Keep it up"}]
        }
        
        response = client.get("/campaigns/camp1/insights?merchant_id=merch_1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["summary"], "Solid campaign.")
        self.assertEqual(data["campaign_id"], "camp1")
        self.assertEqual(len(data["segments"]), 1)

    @patch('analytics.get_campaign_analytics')
    def test_campaign_insights_unauthorized(self, mock_get_analytics):
        self.mock_campaigns.find_one.return_value = None # Fails isolation check
        
        response = client.get("/campaigns/camp1/insights?merchant_id=merch_hacker")
        self.assertEqual(response.status_code, 404)
        mock_get_analytics.assert_not_called()

    @patch('claude_agent.get_client')
    def test_claude_agent_insights_generation(self, mock_get_client):
        """Test the actual generate_campaign_insights function gracefully parses OpenRouter JSON."""
        from claude_agent import generate_campaign_insights
        import json
        
        # Mock OpenAI chat completion
        mock_client = MagicMock()
        mock_response = MagicMock()
        
        expected_json = {
            "summary": "Test Summary",
            "key_insights": ["test1"],
            "recommendations": ["rec1"],
            "segments": []
        }
        
        mock_response.choices[0].message.content = json.dumps(expected_json)
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        result = generate_campaign_insights(
            {"campaign_name": "Test Camp"}, 
            {"total_offers": 10}, 
            []
        )
        
        self.assertEqual(result["summary"], "Test Summary")
        self.assertEqual(result["key_insights"][0], "test1")

    @patch('claude_agent.get_client')
    def test_claude_agent_insights_fallback(self, mock_get_client):
        """Test the fallback mechanism if OpenRouter fails."""
        from claude_agent import generate_campaign_insights
        
        # Simulate network/API failure
        mock_get_client.side_effect = Exception("API Offline")
        
        result = generate_campaign_insights(
            {"campaign_name": "Test Camp"}, 
            {"total_offers": 50, "verified_payments": 5}, 
            [{"segment": "loyal", "verified_payments": 5}]
        )
        
        # Should gracefully return deterministic insight string
        self.assertIn("Test Camp", result["summary"])
        self.assertIn("50", result["summary"])
        self.assertEqual(result["segments"][0]["observation"], "5 conversions")

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    unittest.main()
