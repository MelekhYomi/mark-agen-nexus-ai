"""
Community Engagement & Sentiment Agent
Monitors comments, direct messages, and brand mentions, classifying sentiment and drafting context-aware replies.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List
from app.agents.qwen_client import qwen_client, clean_and_parse_json

logger = logging.getLogger(__name__)


class CommunityEngagementAgent:
    """Classifies incoming customer feedback/comments and drafts responses using Qwen"""
    
    def __init__(self, db, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        
    def process_engagement_stream(self, interactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a batch of comments, brand mentions, or direct messages.
        Categorizes sentiment and drafts ready-to-post responses.
        """
        interactions_str = str(interactions)
        prompt = f"""You are a community manager AI agent.
Analyze the following batch of customer interactions:

{interactions_str}

Evaluate sentiment, detect any urgent issues, and formulate responsive replies.
Return a JSON object with:
1. overall_sentiment_score: float (-1.0 to 1.0, where -1.0 is extremely negative, 1.0 is extremely positive)
2. urgency_count: integer (number of interactions requiring immediate human attention)
3. processed_interactions: list of dicts, each containing:
   - id: string
   - detected_sentiment: string ("POSITIVE", "NEUTRAL", "NEGATIVE")
   - sentiment_score: float
   - issue_category: string ("FAQ", "COMPLAINT", "PRAISE", "OTHER")
   - drafted_reply: string (personalized, highly engaging, empathetic response ready to publish)
   - escalation_required: boolean

Return only a valid JSON object."""

        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a warm, responsive, and professional Customer Success and Community Manager Agent."},
            {"role": "user", "content": prompt}
        ])
        
        raw_content = response["choices"][0]["message"]["content"]
        parsed = clean_and_parse_json(raw_content)
        thinking = response["choices"][0]["message"].get("reasoning_content", "")
        
        return {
            "status": "success",
            "engagement": parsed,
            "thinking": thinking,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
