"""
Ads Manager Agent
Manages ad campaigns, optimizes budgets, and maximizes ROAS.
"""
import logging
from typing import Dict, List
from datetime import datetime
from app.agents.qwen_client import qwen_client, clean_and_parse_json

logger = logging.getLogger(__name__)


class AdsManagerAgent:
    """Manages ad campaigns across platforms"""
    
    def __init__(self, db, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
    
    def optimize_campaigns(self) -> Dict:
        """
        Analyze existing campaigns and provide optimization recommendations.
        Identifies underperformers, suggests budget reallocations, and recommends improvements.
        """
        prompt = """You are an expert media buyer managing multiple ad campaigns.

Analyze campaign performance and provide optimization recommendations:

**Analysis Required:**
1. Identify underperforming campaigns (ROAS < 2.0, CTR < 1%, CPA too high)
2. Identify top performers worth scaling
3. Suggest budget reallocations (move budget from losers to winners)
4. Recommend audience targeting improvements
5. Suggest creative variations to A/B test
6. Identify wasted spend and how to eliminate it

**For each recommendation, provide:**
- action: "pause_campaign", "scale_campaign", "adjust_budget", "change_audience", "test_creative"
- campaign_id or campaign_name
- confidence: 0.0-1.0 (how confident you are this will improve performance)
- expected_impact: estimated improvement percentage
- reason: why you're recommending this

**Budget Rules:**
- Never increase total budget without approval
- Can reallocate between campaigns
- Pause campaigns with ROAS < 1.5 for 7+ days
- Scale campaigns with ROAS > 3.0

Return as structured JSON array of recommendations."""

        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a senior media buyer with $10M+ in ad spend managed. You're data-driven and conservative with budget changes."},
            {"role": "user", "content": prompt}
        ])
        
        optimizations_raw = response["choices"][0]["message"]["content"]
        optimizations = clean_and_parse_json(optimizations_raw)
        thinking = response["choices"][0]["message"].get("reasoning_content", "")
        
        num_recs = len(optimizations) if isinstance(optimizations, list) else str(optimizations_raw).count('"action"')
        
        return {
            "optimizations": optimizations,
            "thinking": thinking,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0),
            "analyzed_at": datetime.utcnow().isoformat(),
            "num_recommendations": num_recs
        }
    
    def create_campaign(
        self, 
        platform: str, 
        objective: str, 
        budget: float, 
        targeting: Dict,
        ad_copy: str = "",
        creative_urls: List[str] = None
    ) -> Dict:
        """Create a new ad campaign"""
        return {
            "campaign_id": f"camp_{platform}_{datetime.utcnow().timestamp()}",
            "platform": platform,
            "objective": objective,
            "budget": budget,
            "targeting": targeting,
            "ad_copy": ad_copy,
            "creative_urls": creative_urls or [],
            "status": "draft",
            "created_at": datetime.utcnow().isoformat()
        }
    
    def adjust_budget(self, campaign_id: str, new_budget: float, reason: str = "") -> Dict:
        """Adjust campaign budget (requires approval if change > 20%)"""
        return {
            "campaign_id": campaign_id,
            "old_budget": 0,  # Would fetch from DB
            "new_budget": new_budget,
            "change_percentage": 0,
            "reason": reason,
            "requires_approval": True,
            "status": "pending_approval"
        }
    
    def pause_campaign(self, campaign_id: str, reason: str = "Low performance") -> Dict:
        """Pause an underperforming campaign"""
        return {
            "campaign_id": campaign_id,
            "status": "paused",
            "reason": reason,
            "paused_at": datetime.utcnow().isoformat()
        }
    
    def generate_ad_copy(
        self, 
        product: str, 
        audience: str, 
        platform: str,
        angle: str = "benefits"
    ) -> Dict:
        """Generate multiple ad copy variations"""
        prompt = f"""Create 3 high-converting ad copy variations for {platform} ads.

Product: {product}
Target Audience: {audience}
Angle: {angle}

For each variation provide:
1. headline: Attention-grabbing headline (max 40 chars)
2. primary_text: Main ad copy (2-4 sentences)
3. description: Short description (max 90 chars)
4. cta: Call-to-action button text
5. emotional_trigger: What emotion this targets

Return as JSON array."""
        
        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a direct response copywriter specializing in high-converting ads"},
            {"role": "user", "content": prompt}
        ])
        
        variations_raw = response["choices"][0]["message"]["content"]
        variations = clean_and_parse_json(variations_raw)
        
        return {
            "variations": variations,
            "platform": platform,
            "product": product,
            "audience": audience,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0)
        }
    
    def calculate_roas(self, spend: float, revenue: float) -> float:
        """Calculate Return on Ad Spend"""
        if spend == 0:
            return 0.0
        return revenue / spend
    
    def recommend_budget_allocation(
        self, 
        campaigns: List[Dict],
        total_budget: float
    ) -> Dict:
        """Recommend optimal budget allocation across campaigns"""
        prompt = f"""Given these campaigns and their performance:
{campaigns}

Total available budget: ${total_budget}

Recommend optimal budget allocation to maximize ROAS.
For each campaign, provide:
- campaign_id
- recommended_budget
- reasoning
- expected_roas

Return as JSON array."""
        
        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a budget optimization expert"},
            {"role": "user", "content": prompt}
        ])
        
        allocation_raw = response["choices"][0]["message"]["content"]
        allocation = clean_and_parse_json(allocation_raw)
        
        return {
            "allocation": allocation,
            "total_budget": total_budget,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0)
        }