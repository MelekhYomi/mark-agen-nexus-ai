"""
Market Intelligence & Scraping Agent
Monitors competitor campaigns, trending social hashtags, and industry keywords using Qwen.
"""
import logging
from datetime import datetime
from typing import Dict, Any
from app.agents.qwen_client import qwen_client, clean_and_parse_json

logger = logging.getLogger(__name__)


class MarketIntelligenceAgent:
    """Monitors competitor campaigns, industry trends, and keywords"""
    
    def __init__(self, db, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        
    def generate_competitor_brief(self, industry_niche: str) -> Dict[str, Any]:
        """
        Analyze current trend data and competitor angles to formulate an intelligence brief.
        """
        prompt = f"""You are an elite Market Research & Competitor Intelligence AI.
Formulate a strategic market briefing for the niche: "{industry_niche}"

Conduct competitive analysis and return a JSON object with:
1. market_niche: string
2. top_competitors: list of dicts, each with:
   - name: string
   - core_strength: string
   - observed_ad_angles: list of strings (their current messaging strategies)
3. trending_hashtags_and_keywords: list of strings
4. viral_triggers: list of strings (elements driving high engagement in this space)
5. strategic_gaps: list of strings (untapped opportunities our brand can exploit)

Return as a valid JSON object."""

        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a sharp, forward-looking Business Intelligence Analyst and Competitive Researcher."},
            {"role": "user", "content": prompt}
        ])
        
        raw_content = response["choices"][0]["message"]["content"]
        parsed = clean_and_parse_json(raw_content)
        thinking = response["choices"][0]["message"].get("reasoning_content", "")
        
        return {
            "status": "success",
            "brief": parsed,
            "thinking": thinking,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
