"""
Brand & Compliance Guardian Agent
Audits and moderates generated content for brand voice consistency, safety, and legal compliance.
"""
import logging
from datetime import datetime
from typing import Dict, Any
from app.agents.qwen_client import qwen_client, clean_and_parse_json

logger = logging.getLogger(__name__)


class BrandGuardianAgent:
    """Audits generated content for compliance and brand voice alignment"""
    
    def __init__(self, db, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        
    def audit_content(self, content: str, platform: str) -> Dict[str, Any]:
        """
        Audits a drafted social media post or marketing asset.
        Returns risk scores, compliance ratings, and suggested rewrites if necessary.
        """
        prompt = f"""You are an elite Brand Voice & Legal Compliance Guardian AI.
Your job is to audit a draft post for brand alignment, legal risks, copyright infringements, and tone.

Platform: {platform}
Draft Content: "{content}"

Perform a thorough audit and return a JSON object with the following fields:
1. approved: boolean (true if risk_score < 0.4 and compliance_score >= 0.7)
2. risk_score: float (0.0 to 1.0, where 1.0 is extremely controversial/risky)
3. compliance_score: float (0.0 to 1.0, where 1.0 is fully compliant with standard advertising rules)
4. brand_voice_alignment: float (0.0 to 1.0, where 1.0 matches a professional, premium tone perfectly)
5. issues_found: list of strings (specific warnings or copyright/compliance problems)
6. suggested_rewrite: string (a brand-safe, highly engaging version of the post maintaining the original message but fixing issues)

Ensure the output is valid JSON."""

        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a brand alignment and legal compliance officer with 15+ years of advertising law experience."},
            {"role": "user", "content": prompt}
        ])
        
        raw_content = response["choices"][0]["message"]["content"]
        parsed = clean_and_parse_json(raw_content)
        thinking = response["choices"][0]["message"].get("reasoning_content", "")
        
        return {
            "status": "success",
            "audit": parsed,
            "thinking": thinking,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
