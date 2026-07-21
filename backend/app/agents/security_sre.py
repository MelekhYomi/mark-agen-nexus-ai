"""
SRE & Security Audit Agent
Monitors transaction tables, backend query sequences, and access logs to detect security threats and system vulnerabilities.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List
from app.agents.qwen_client import qwen_client, clean_and_parse_json

logger = logging.getLogger(__name__)


class SecuritySREAgent:
    """Audits system security and access patterns, flagging SQL injection or brute force threats"""
    
    def __init__(self, db, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        
    def audit_system_security(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a batch of system access/request logs for SQL injections, brute-force logins,
        cross-tenant leakage, or performance vulnerabilities.
        """
        logs_str = str(logs)
        prompt = f"""You are an elite DevOps SRE & Security Compliance Guard AI.
Audit the following batch of system logs and database queries:

{logs_str}

Analyze for:
- SQL injection patterns
- Authentication brute force attempts
- Unusual API payload structures
- Row-Level Security (RLS) leakage risks

Return a JSON object with:
1. secure: boolean (true if threat_level is "LOW")
2. threat_level: string ("LOW", "MEDIUM", "HIGH")
3. anomalies_detected: list of dicts, each containing:
   - source_ip: string
   - threat_category: string ("SQL_INJECTION", "BRUTE_FORCE", "RLS_VIOLATION", "NONE")
   - confidence_score: float (0.0 to 1.0)
   - description: string
4. auto_mitigation_actions: list of strings (e.g., "IP_BLOCK", "RATE_LIMIT_STRICTEN", "LOCK_USER_ACCOUNT")
5. audit_summary: string

Return only a valid JSON object."""

        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a senior DevSecOps engineer and white-hat security researcher with extensive experience in system hardening."},
            {"role": "user", "content": prompt}
        ])
        
        raw_content = response["choices"][0]["message"]["content"]
        parsed = clean_and_parse_json(raw_content)
        thinking = response["choices"][0]["message"].get("reasoning_content", "")
        
        return {
            "status": "success",
            "security_audit": parsed,
            "thinking": thinking,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
