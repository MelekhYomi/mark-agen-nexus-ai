"""
Conversion & A/B Optimizer Agent
Monitors marketing performance data, evaluates ad copies, and optimizes conversion paths and budgets.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List
from app.agents.qwen_client import qwen_client, clean_and_parse_json

logger = logging.getLogger(__name__)


class ConversionOptimizerAgent:
    """Evaluates campaign ROI, drafts A/B test variations, and reallocates ad spend"""
    
    def __init__(self, db, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        
    def optimize_conversion_funnels(self, campaigns_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze performance stats of active campaigns and suggest conversion optimizations,
        A/B tests, and budget shifts.
        """
        data_str = str(campaigns_data)
        prompt = f"""You are a senior Conversion Rate Optimization (CRO) AI expert.
Analyze the following active campaign performance metrics:

{data_str}

Evaluate metrics such as CTR (Click-Through Rate), CPC (Cost Per Click), CPA (Cost Per Acquisition), and conversions.
Develop dynamic optimization suggestions and return a JSON object with:
1. campaign_evaluations: list of dicts, each with:
   - campaign_id: string
   - health_status: string ("EXCELLENT", "STABLE", "UNDERPERFORMING")
   - bottle_neck_analysis: string
   - recommended_budget_shift: float (percentage increase or decrease)
2. ab_test_suggestions: list of dicts, each with:
   - target_campaign_id: string
   - variable_to_test: string ("headline", "cta", "audience")
   - variant_a: string (current version baseline)
   - variant_b: string (Qwen optimized high-converting alternative)
3. predicted_roi_uplift: float (estimated percentage increase in conversions if suggestions implemented)

Return only a valid JSON object matching these specifications."""

        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are an elite Growth Marketer and A/B testing specialist who lives and breathes data, conversions, and ROI metrics."},
            {"role": "user", "content": prompt}
        ])
        
        raw_content = response["choices"][0]["message"]["content"]
        parsed = clean_and_parse_json(raw_content)
        thinking = response["choices"][0]["message"].get("reasoning_content", "")
        
        return {
            "status": "success",
            "optimizations": parsed,
            "thinking": thinking,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
