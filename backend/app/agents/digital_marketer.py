"""
Digital Marketer Agent
Develops comprehensive marketing strategies and coordinates campaigns.
"""
import logging
from typing import Dict, List
from datetime import datetime
from app.agents.qwen_client import qwen_client, clean_and_parse_json

logger = logging.getLogger(__name__)


class DigitalMarketerAgent:
    """Develops marketing strategies and coordinates campaigns"""
    
    def __init__(self, db, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
    
    def develop_strategy(self, focus_area: str = "growth") -> Dict:
        """
        Create comprehensive marketing strategy based on current trends and goals.
        """
        prompt = f"""You are a senior digital marketing strategist with expertise in {focus_area}.

Create a comprehensive 30-day marketing strategy that includes:

1. **Target Audience Analysis**
   - Primary audience demographics
   - Pain points and motivations
   - Where they spend time online

2. **Content Pillars** (3-5 main topics)
   - Topic name
   - Why it resonates with audience
   - Content formats that work best

3. **Channel Strategy**
   - Which platforms to prioritize
   - Posting frequency for each
   - Content type mix

4. **Campaign Ideas** (3 campaigns for next 30 days)
   - Campaign name
   - Objective
   - Target audience
   - Key messaging
   - Success metrics

5. **KPIs to Track**
   - Primary metrics
   - Secondary metrics
   - Target values

Return as structured JSON."""

        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a Fortune 500 marketing strategist. Your strategies are data-driven and results-focused."},
            {"role": "user", "content": prompt}
        ])
        
        strategy_raw = response["choices"][0]["message"]["content"]
        strategy = clean_and_parse_json(strategy_raw)
        thinking = response["choices"][0]["message"].get("reasoning_content", "")
        
        return {
            "strategy": strategy,
            "thinking": thinking,
            "focus_area": focus_area,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def analyze_competitors(self, competitors: List[str]) -> Dict:
        """Analyze competitor strategies and identify opportunities"""
        competitors_str = ", ".join(competitors)
        
        prompt = f"""Analyze these competitors: {competitors_str}

For each competitor, provide:
1. Their content strategy (what they post, how often)
2. Their strengths (what they do well)
3. Their weaknesses (gaps we can exploit)
4. Engagement rate estimate
5. Key differentiators

Then provide:
- 3 opportunities we can capitalize on
- 3 threats we should watch for
- Recommended positioning strategy

Return as structured JSON."""
        
        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a competitive intelligence expert"},
            {"role": "user", "content": prompt}
        ])
        
        analysis_raw = response["choices"][0]["message"]["content"]
        analysis = clean_and_parse_json(analysis_raw)
        
        return {
            "analysis": analysis,
            "competitors_analyzed": len(competitors),
            "tokens_used": response.get("usage", {}).get("total_tokens", 0)
        }
    
    def plan_campaign(
        self, 
        objective: str, 
        budget: float, 
        duration_days: int,
        target_audience: str = ""
    ) -> Dict:
        """Plan a detailed marketing campaign"""
        prompt = f"""Plan a marketing campaign with these parameters:
- Objective: {objective}
- Budget: ${budget}
- Duration: {duration_days} days
- Target Audience: {target_audience or 'General audience'}

Provide:
1. Campaign name and tagline
2. Channel mix (which platforms, budget allocation)
3. Content calendar (key dates and posts)
4. Ad creative concepts (3 variations)
5. Landing page recommendations
6. Success metrics and targets
7. Risk factors and mitigation

Return as structured JSON."""
        
        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a campaign planning expert"},
            {"role": "user", "content": prompt}
        ])
        
        campaign_raw = response["choices"][0]["message"]["content"]
        campaign_plan = clean_and_parse_json(campaign_raw)
        
        return {
            "campaign_plan": campaign_plan,
            "objective": objective,
            "budget": budget,
            "duration_days": duration_days,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0)
        }
    
    def generate_copy_variations(self, product: str, angle: str, count: int = 5) -> List[str]:
        """Generate multiple copy variations for testing"""
        prompt = f"Generate {count} different marketing copy variations for {product} using the angle: {angle}. Each should be 2-3 sentences. Return as a numbered list."
        
        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a conversion copywriter"},
            {"role": "user", "content": prompt}
        ])
        
        variations_raw = response["choices"][0]["message"]["content"]
        variations = clean_and_parse_json(variations_raw)
        
        return {
            "variations": variations,
            "product": product,
            "angle": angle,
            "count": count
        }