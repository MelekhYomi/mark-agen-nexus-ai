"""
Dynamic CFO & Subscription Optimizer Agent
Audits system transactions, subscription configurations, and workspace usage to prevent churn and optimize revenue.
"""
import logging
from datetime import datetime
from typing import Dict, Any
from app.agents.qwen_client import qwen_client, clean_and_parse_json

logger = logging.getLogger(__name__)


class DynamicCFOAgent:
    """Optimizes subscription health, recovers payments, and recommends optimal price points"""
    
    def __init__(self, db, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        
    def analyze_subscription_health(self, billing_history: Dict[str, Any], active_usage: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze current billing transactions and client activity levels to identify churn risks
        and propose financial optimization triggers.
        """
        history_str = str(billing_history)
        usage_str = str(active_usage)
        
        prompt = f"""You are a dynamic CFO and Revenue Optimization AI.
Analyze the current client's transaction history and workspace activity level:

Billing Profile:
{history_str}

Usage Statistics:
{usage_str}

Evaluate metrics such as payment frequency, API limits used, and login activity.
Return a JSON object containing:
1. billing_health_grade: string ("A", "B", "C", "D", "F")
2. churn_risk_percentage: float (0.0 to 100.0)
3. recommended_pricing_tier: string ("LITE", "PRO", "ENTERPRISE")
4. optimization_triggers: list of dicts, each containing:
   - trigger_name: string (e.g., "PAYMENT_RECOVERY_OFFER", "API_UPSELL", "PROACTIVE_CHURN_DISCOUNT")
   - customized_offer_headline: string
   - action_logic: string (when/how to auto-deploy the offer via Stripe)
   - dynamic_copysnippet: string (hyper-personalized Qwen outreach copy designed to retain this client)

Return only a valid JSON object."""

        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a savvy Chief Financial Officer and SaaS Pricing Strategist who knows how to optimize pricing loops and retain tenants."},
            {"role": "user", "content": prompt}
        ])
        
        raw_content = response["choices"][0]["message"]["content"]
        parsed = clean_and_parse_json(raw_content)
        thinking = response["choices"][0]["message"].get("reasoning_content", "")
        
        return {
            "status": "success",
            "revenue_optimization": parsed,
            "thinking": thinking,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
