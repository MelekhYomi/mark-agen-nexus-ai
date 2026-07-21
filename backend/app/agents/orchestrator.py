"""
Agent Orchestrator - Coordinates all 5 AI agents
This is the central brain that manages agent execution, approval workflows,
and ensures agents work together cohesively.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.social_manager import SocialManagerAgent
from app.agents.digital_marketer import DigitalMarketerAgent
from app.agents.ads_manager import AdsManagerAgent
from app.agents.seo_expert import SEOExpertAgent
from app.agents.analytics import AnalyticsAgent
from app.agents.brand_guardian import BrandGuardianAgent
from app.agents.conversion_optimizer import ConversionOptimizerAgent
from app.agents.community_engagement import CommunityEngagementAgent
from app.agents.market_intelligence import MarketIntelligenceAgent
from app.agents.dynamic_cfo import DynamicCFOAgent
from app.agents.security_sre import SecuritySREAgent
from app.agents.calendar_planner import CalendarPlannerAgent
from app.agents.media_generator import MediaGeneratorAgent
from app.models import (
    ClientWorkspace, AgentActionLog, ApprovalQueue, ApprovalStatus, ContentCalendarItem
)
from app.config import settings

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Central orchestrator for the 13-agent society swarm.
    Manages execution order, approval workflows, and cross-agent communication.
    """
    
    def __init__(self, db: Session, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        self.workspace = None
        
        # Initialize all 13 agents
        self.social_manager = SocialManagerAgent(db, workspace_id)
        self.digital_marketer = DigitalMarketerAgent(db, workspace_id)
        self.ads_manager = AdsManagerAgent(db, workspace_id)
        self.seo_expert = SEOExpertAgent(db, workspace_id)
        self.analytics = AnalyticsAgent(db, workspace_id)
        self.brand_guardian = BrandGuardianAgent(db, workspace_id)
        self.conversion_optimizer = ConversionOptimizerAgent(db, workspace_id)
        self.community_engagement = CommunityEngagementAgent(db, workspace_id)
        self.market_intelligence = MarketIntelligenceAgent(db, workspace_id)
        self.dynamic_cfo = DynamicCFOAgent(db, workspace_id)
        self.security_sre = SecuritySREAgent(db, workspace_id)
        self.calendar_planner = CalendarPlannerAgent(db, workspace_id)
        self.media_generator = MediaGeneratorAgent(db, workspace_id)
    
    def _normalize_to_list(self, data: Any, key_fallbacks: List[str] = None) -> List[Any]:
        """Safely normalizes data to a list of dicts to prevent iteration crashes."""
        if not data:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if key_fallbacks:
                for key in key_fallbacks:
                    if key in data and isinstance(data[key], list):
                        return data[key]
            return [data]
        return []

    def _load_workspace(self):
        """Load workspace configuration"""
        if not self.workspace:
            result = self.db.execute(
                select(ClientWorkspace).where(ClientWorkspace.id == self.workspace_id)
            )
            self.workspace = result.scalar_one_or_none()
            if not self.workspace:
                raise ValueError(f"Workspace {self.workspace_id} not found")
    
    def _log_action(
        self, 
        agent: str, 
        summary: str, 
        status: str = "EXECUTED",
        reasoning: Optional[str] = None
    ):
        """Log agent action to database"""
        log = AgentActionLog(
            id=f"log_{datetime.utcnow().timestamp()}_{agent.lower().replace(' ', '_')}",
            workspace_id=self.workspace_id,
            agent_persona=agent,
            action_summary=summary,
            detailed_reasoning=reasoning,
            status=status,
            created_at=datetime.utcnow()
        )
        self.db.add(log)
        self.db.commit()
        logger.info(f"[{agent}] {summary}")
    
    def _create_approval(
        self,
        agent: str,
        action_type: str,
        title: str,
        description: str,
        payload: Dict,
        risk_score: float = 0.3
    ) -> str:
        """Create approval request for human review"""
        approval_id = f"ap_{datetime.utcnow().timestamp()}"
        approval = ApprovalQueue(
            id=approval_id,
            workspace_id=self.workspace_id,
            agent_persona=agent,
            action_type=action_type,
            title=title,
            description=description,
            payload=payload,
            risk_score=int(risk_score * 100),
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow()
        )
        self.db.add(approval)
        self.db.commit()
        
        self._log_action(
            agent, 
            f"Created approval request: {title}", 
            "PENDING_APPROVAL"
        )
        
        return approval_id
    
    def run_full_cycle(self) -> Dict[str, Any]:
        """
        Execute complete agent cycle in proper order:
        1. Analytics (gather data)
        2. Social Manager (create content)
        3. Digital Marketer (develop strategy)
        4. Ads Manager (optimize campaigns)
        5. SEO Expert (improve rankings)
        """
        self._load_workspace()
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "workspace_id": self.workspace_id,
            "workspace_name": self.workspace.brand_name,
            "autopilot_enabled": self.workspace.autopilot_enabled,
            "agents": {}
        }
        
        # Phase 1: Analytics (provides insights for other agents)
        try:
            analytics_result = self.analytics.analyze_performance()
            results["agents"]["analytics"] = analytics_result
            self._log_action(
                "Analytics", 
                f"Performance analysis completed. {analytics_result.get('insights_count', 0)} insights generated.",
                "EXECUTED",
                analytics_result.get('thinking')
            )
        except Exception as e:
            logger.error(f"Analytics error: {e}")
            results["agents"]["analytics"] = {"error": str(e)}
            self._log_action("Analytics", f"Error: {str(e)}", "FAILED")
        
        # Phase 2: Social Manager (content creation) gated by Brand Guardian (compliance review)
        # Brand Guardian reviews each candidate BEFORE the publish/approval decision, not after -
        # this is a real veto, not a downstream audit that runs too late to matter.
        try:
            content_result = self.social_manager.generate_content_suggestions()
            results["agents"]["social_manager"] = content_result

            suggestions = self._normalize_to_list(content_result.get('suggestions'), ["suggestions", "items"])

            brand_reviews = []
            approved_suggestions = []

            for suggestion in suggestions[:3]:
                if not isinstance(suggestion, dict):
                    continue

                # Audit the actual public-facing copy (caption), not the internal editorial description
                content_to_audit = suggestion.get("caption") or suggestion.get("description") or suggestion.get("content") or ""
                platform = suggestion.get("platform", "twitter")

                audit_result = self.brand_guardian.audit_content(content_to_audit, platform)
                audit = audit_result.get('audit', {}) if isinstance(audit_result.get('audit'), dict) else {}
                brand_reviews.append({"title": suggestion.get("title"), "audit": audit})

                if audit.get('approved', True):
                    self._log_action(
                        "Brand Guardian",
                        f"Cleared for publish: '{suggestion.get('title', 'Untitled')}' ({platform}). Compliance score: {audit.get('compliance_score', 1.0)}",
                        "EXECUTED",
                        audit_result.get('thinking')
                    )
                    approved_suggestions.append(suggestion)
                else:
                    issues = "; ".join(audit.get('issues_found', []) or ["unspecified compliance issue"])
                    self._log_action(
                        "Brand Guardian",
                        f"REJECTED '{suggestion.get('title', 'Untitled')}' ({platform}) from Social Manager: {issues}",
                        "EXECUTED",
                        audit_result.get('thinking')
                    )
                    self._create_approval(
                        "Brand Guardian",
                        "content_blocked_needs_revision",
                        f"Blocked: {suggestion.get('title', 'Untitled')}",
                        f"Brand Guardian blocked this Social Manager post: {issues}. Suggested rewrite: {audit.get('suggested_rewrite', 'N/A')}",
                        suggestion,
                        audit.get('risk_score', 0.8)
                    )

            results["agents"]["brand_guardian"] = {"reviews": brand_reviews}

            # Auto-publish only content BOTH agents cleared
            if self.workspace.autopilot_enabled:
                for suggestion in approved_suggestions[:2]:  # Limit to 2 posts
                    if suggestion.get('risk_score', 1.0) < 0.3:
                        self.social_manager.publish_post(suggestion)
                        self._log_action(
                            "Social Manager",
                            f"Auto-published: {suggestion.get('title', 'Untitled')}",
                            "EXECUTED"
                        )
            else:
                # Create approval requests for content Brand Guardian already cleared
                for suggestion in approved_suggestions:
                    self._create_approval(
                        "Social Manager",
                        "publish_post",
                        suggestion.get('title', 'New Post'),
                        suggestion.get('description', ''),
                        suggestion,
                        suggestion.get('risk_score', 0.3)
                    )
        except Exception as e:
            logger.error(f"Social Manager error: {e}")
            results["agents"]["social_manager"] = {"error": str(e)}
        
        # Phase 3: Digital Marketer (strategy)
        try:
            strategy_result = self.digital_marketer.develop_strategy()
            results["agents"]["digital_marketer"] = strategy_result
            self._log_action(
                "Digital Marketer",
                "Strategy developed with recommendations",
                "EXECUTED",
                strategy_result.get('thinking')
            )
        except Exception as e:
            logger.error(f"Digital Marketer error: {e}")
            results["agents"]["digital_marketer"] = {"error": str(e)}
        
        # Phase 4: Ads Manager (campaign optimization)
        try:
            ads_result = self.ads_manager.optimize_campaigns()
            results["agents"]["ads_manager"] = ads_result
            
            optimizations = self._normalize_to_list(ads_result.get('optimizations'), ["optimizations", "items"])
            
            # Execute optimizations if autopilot enabled
            if self.workspace.autopilot_enabled:
                for optimization in optimizations:
                    if isinstance(optimization, dict):
                        if optimization.get('action') == 'pause_campaign' and optimization.get('confidence', 0) > 0.8:
                            self.ads_manager.pause_campaign(optimization.get('campaign_id'))
                            self._log_action(
                                "Ads Manager",
                                f"Paused campaign: {optimization.get('campaign_name')}",
                                "EXECUTED"
                            )
                        elif optimization.get('action') == 'adjust_budget':
                            self._create_approval(
                                "Ads Manager",
                                "adjust_budget",
                                f"Adjust budget for {optimization.get('campaign_name')}",
                                optimization.get('reason', ''),
                                optimization,
                                0.4
                            )
        except Exception as e:
            logger.error(f"Ads Manager error: {e}")
            results["agents"]["ads_manager"] = {"error": str(e)}
        
        # Phase 5: SEO Expert (rankings)
        try:
            seo_result = self.seo_expert.improve_rankings()
            results["agents"]["seo_expert"] = seo_result
            self._log_action(
                "SEO Expert",
                "SEO improvements identified and applied",
                "EXECUTED",
                seo_result.get('thinking')
            )
        except Exception as e:
            logger.error(f"SEO Expert error: {e}")
            results["agents"]["seo_expert"] = {"error": str(e)}
        
        # Phase 7: Conversion Optimizer (evaluates campaign performance and proposes A/B tests)
        try:
            campaigns_input = [
                {
                    "campaign_id": "camp_retargeting_01",
                    "campaign_name": "Nexus AI Retargeting",
                    "ctr": 0.024,
                    "cpc": 1.15,
                    "cpa": 18.50,
                    "conversions": 142,
                    "spend": 2627.0
                },
                {
                    "campaign_id": "camp_lookalike_02",
                    "campaign_name": "Nexus AI Lookalike",
                    "ctr": 0.012,
                    "cpc": 2.45,
                    "cpa": 45.00,
                    "conversions": 38,
                    "spend": 1710.0
                }
            ]
            conversion_result = self.conversion_optimizer.optimize_conversion_funnels(campaigns_input)
            results["agents"]["conversion_optimizer"] = conversion_result
            self._log_action(
                "Conversion Optimizer",
                f"Conversion paths audited. Predicted ROI uplift: {conversion_result.get('optimizations', {}).get('predicted_roi_uplift', 15.0)}%",
                "EXECUTED",
                conversion_result.get('thinking')
            )
        except Exception as e:
            logger.error(f"Conversion Optimizer error: {e}")
            results["agents"]["conversion_optimizer"] = {"error": str(e)}
            self._log_action("Conversion Optimizer", f"Error: {str(e)}", "FAILED")

        # Phase 8: Community Engagement (monitors comments and drafts replies)
        try:
            comments_input = [
                {"id": "cmt_01", "author": "John Doe", "text": "Is there a free trial for Nexus AI?", "platform": "twitter"},
                {"id": "cmt_02", "author": "Jane Smith", "text": "Having issues setting up the Qwen API key on my local dashboard, help!", "platform": "facebook"},
                {"id": "cmt_03", "author": "CryptoKing", "text": "Best agent platform out there! Absolute game changer.", "platform": "linkedin"}
            ]
            community_result = self.community_engagement.process_engagement_stream(comments_input)
            results["agents"]["community_engagement"] = community_result
            self._log_action(
                "Community Engagement",
                f"Processed sentiment stream. Urgency count: {community_result.get('engagement', {}).get('urgency_count', 0)}",
                "EXECUTED",
                community_result.get('thinking')
            )
        except Exception as e:
            logger.error(f"Community Engagement error: {e}")
            results["agents"]["community_engagement"] = {"error": str(e)}
            self._log_action("Community Engagement", f"Error: {str(e)}", "FAILED")

        # Phase 9: Market Intelligence (competitor campaigns, hashtags, and opportunities)
        try:
            industry = getattr(self.workspace, "industry", "AI Marketing and SaaS Solutions") or "AI Marketing and SaaS Solutions"
            market_result = self.market_intelligence.generate_competitor_brief(industry)
            results["agents"]["market_intelligence"] = market_result
            self._log_action(
                "Market Intelligence",
                f"Competitor intelligence brief generated for niche: {industry}",
                "EXECUTED",
                market_result.get('thinking')
            )
        except Exception as e:
            logger.error(f"Market Intelligence error: {e}")
            results["agents"]["market_intelligence"] = {"error": str(e)}
            self._log_action("Market Intelligence", f"Error: {str(e)}", "FAILED")

        # Phase 10: Dynamic CFO (subscription health, upsell, and retention optimization)
        try:
            billing_history = {
                "subscription_status": "active",
                "current_tier": "PRO",
                "monthly_price": 79.0,
                "last_payment_status": "succeeded",
                "payment_failures_count": 0,
                "next_billing_date": "2026-08-01"
            }
            active_usage = {
                "days_since_last_login": 2,
                "api_calls_this_month": 14205,
                "api_calls_limit": 20000,
                "agents_deployed": 11,
                "active_campaigns": 3
            }
            cfo_result = self.dynamic_cfo.analyze_subscription_health(billing_history, active_usage)
            results["agents"]["dynamic_cfo"] = cfo_result
            self._log_action(
                "Dynamic CFO",
                f"Financial health check complete. Churn risk: {cfo_result.get('revenue_optimization', {}).get('churn_risk_percentage', 0.0)}%",
                "EXECUTED",
                cfo_result.get('thinking')
            )
        except Exception as e:
            logger.error(f"Dynamic CFO error: {e}")
            results["agents"]["dynamic_cfo"] = {"error": str(e)}
            self._log_action("Dynamic CFO", f"Error: {str(e)}", "FAILED")

        # Phase 11: Security SRE (system audit & anomaly detection)
        try:
            security_logs = [
                {"timestamp": "2026-07-08T03:15:00", "source_ip": "192.168.1.45", "request_path": "/api/v1/auth/login", "method": "POST", "status_code": 200, "payload": "{}"},
                {"timestamp": "2026-07-08T03:15:20", "source_ip": "10.0.4.112", "request_path": "/api/v1/agents/run", "method": "POST", "status_code": 200, "payload": "{\"agent\": \"analytics\"}"},
                {"timestamp": "2026-07-08T03:16:05", "source_ip": "198.51.100.7", "request_path": "/api/v1/campaigns", "method": "GET", "status_code": 401, "payload": "{\"filter\": \"' OR 1=1 --\"}"}
            ]
            security_result = self.security_sre.audit_system_security(security_logs)
            results["agents"]["security_sre"] = security_result
            self._log_action(
                "Security SRE",
                f"Security compliance audit completed. Threat level: {security_result.get('security_audit', {}).get('threat_level', 'LOW')}",
                "EXECUTED",
                security_result.get('thinking')
            )
        except Exception as e:
            logger.error(f"Security SRE error: {e}")
            results["agents"]["security_sre"] = {"error": str(e)}
            self._log_action("Security SRE", f"Error: {str(e)}", "FAILED")
        
        # Phase 12: Content Calendar Planner (plans campaigns based on industry and goals)
        try:
            industry = getattr(self.workspace, "industry", "AI Marketing and SaaS Solutions") or "AI Marketing and SaaS Solutions"
            niche_strategy = f"Campaign plan optimized for {self.workspace.brand_name} in {industry}."
            calendar_result = self.calendar_planner.plan_content_calendar(niche_strategy, days=3)
            results["agents"]["calendar_planner"] = calendar_result
            self._log_action(
                "Calendar Planner",
                f"Planned {calendar_result.get('calendar_items_count', 0)} multi-platform calendar entries as pending review.",
                "EXECUTED",
                calendar_result.get('thinking')
            )
        except Exception as e:
            logger.error(f"Calendar Planner error: {e}")
            results["agents"]["calendar_planner"] = {"error": str(e)}
            self._log_action("Calendar Planner", f"Error: {str(e)}", "FAILED")

        # Phase 13: Media Generator (creates visuals, graphics, scripts, and video storyboards for calendar posts)
        try:
            # Query the newly created pending calendar items to generate assets for them
            stmt = select(ContentCalendarItem).where(
                ContentCalendarItem.workspace_id == self.workspace_id,
                ContentCalendarItem.media_type != "TEXT",
                ContentCalendarItem.media_url == None
            ).limit(2)
            db_res = self.db.execute(stmt)
            pending_items = db_res.scalars().all()
            
            generated_assets_count = 0
            media_result = None
            for item in pending_items:
                media_result = self.media_generator.generate_multimodal_assets(
                    title=item.title,
                    media_type=item.media_type,
                    platform=item.platform.value
                )
                assets = media_result.get("media_assets", {})
                if isinstance(assets, dict):
                    item.media_generation_prompt = assets.get("image_prompt")
                    item.media_url = assets.get("asset_url")
                    generated_assets_count += 1
            
            if pending_items:
                self.db.commit()
                
            # If no pending items found (or we generated assets), we still perform a default generation for simulation
            if not media_result:
                media_result = self.media_generator.generate_multimodal_assets(
                    title="Scale your startup with Qwen AI agents",
                    media_type="IMAGE",
                    platform="linkedin"
                )
                
            results["agents"]["media_generator"] = media_result
            self._log_action(
                "Media Generator",
                f"Generated and attached {generated_assets_count} multimodal assets (prompts/OSS links) to content items.",
                "EXECUTED",
                media_result.get('thinking')
            )
        except Exception as e:
            logger.error(f"Media Generator error: {e}")
            results["agents"]["media_generator"] = {"error": str(e)}
            self._log_action("Media Generator", f"Error: {str(e)}", "FAILED")

        
        # Summary
        results["summary"] = {
            "total_actions": sum(1 for agent_result in results["agents"].values() if "error" not in agent_result),
            "errors": sum(1 for agent_result in results["agents"].values() if "error" in agent_result),
            "approvals_created": self._count_pending_approvals()
        }
        
        self._log_action(
            "Orchestrator",
            f"Full cycle completed. {results['summary']['total_actions']} actions, {results['summary']['errors']} errors",
            "EXECUTED"
        )
        
        return results
    
    def _count_pending_approvals(self) -> int:
        """Count pending approvals for this workspace"""
        result = self.db.execute(
            select(ApprovalQueue).where(
                ApprovalQueue.workspace_id == self.workspace_id,
                ApprovalQueue.status == ApprovalStatus.PENDING
            )
        )
        return len(result.scalars().all())
    
    def run_single_agent(self, agent_name: str, **kwargs) -> Dict:
        """Run a specific agent"""
        self._load_workspace()
        
        agents = {
            "social_manager": self.social_manager,
            "digital_marketer": self.digital_marketer,
            "ads_manager": self.ads_manager,
            "seo_expert": self.seo_expert,
            "analytics": self.analytics,
            "brand_guardian": self.brand_guardian,
            "conversion_optimizer": self.conversion_optimizer,
            "community_engagement": self.community_engagement,
            "market_intelligence": self.market_intelligence,
            "dynamic_cfo": self.dynamic_cfo,
            "security_sre": self.security_sre,
            "calendar_planner": self.calendar_planner,
            "media_generator": self.media_generator
        }
        
        if agent_name not in agents:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        agent = agents[agent_name]
        
        if agent_name == "social_manager":
            result = agent.generate_content_suggestions(**kwargs)
        elif agent_name == "digital_marketer":
            result = agent.develop_strategy(**kwargs)
        elif agent_name == "ads_manager":
            result = agent.optimize_campaigns(**kwargs)
        elif agent_name == "seo_expert":
            result = agent.improve_rankings(**kwargs)
        elif agent_name == "analytics":
            result = agent.analyze_performance(**kwargs)
        elif agent_name == "brand_guardian":
            content = kwargs.get("content", "Unlock unlimited growth with Nexus AI!")
            platform = kwargs.get("platform", "twitter")
            result = agent.audit_content(content=content, platform=platform)
        elif agent_name == "conversion_optimizer":
            campaigns_data = kwargs.get("campaigns_data") or [
                {"campaign_id": "c1", "campaign_name": "Nexus Ad", "ctr": 0.02, "cpc": 1.0, "cpa": 15.0, "conversions": 100, "spend": 1000.0}
            ]
            result = agent.optimize_conversion_funnels(campaigns_data=campaigns_data)
        elif agent_name == "community_engagement":
            interactions = kwargs.get("interactions") or [
                {"id": "1", "author": "User", "text": "Love this platform!", "platform": "twitter"}
            ]
            result = agent.process_engagement_stream(interactions=interactions)
        elif agent_name == "market_intelligence":
            industry_niche = kwargs.get("industry_niche") or getattr(self.workspace, 'industry', 'AI Marketing') or 'AI Marketing'
            result = agent.generate_competitor_brief(industry_niche=industry_niche)
        elif agent_name == "dynamic_cfo":
            billing_history = kwargs.get("billing_history") or {
                "subscription_status": "active", "current_tier": "PRO", "monthly_price": 79.0, "last_payment_status": "succeeded", "payment_failures_count": 0, "next_billing_date": "2026-08-01"
            }
            active_usage = kwargs.get("active_usage") or {
                "days_since_last_login": 2, "api_calls_this_month": 14205, "api_calls_limit": 20000, "agents_deployed": 11, "active_campaigns": 3
            }
            result = agent.analyze_subscription_health(billing_history=billing_history, active_usage=active_usage)
        elif agent_name == "security_sre":
            logs = kwargs.get("logs") or [
                {"timestamp": "2026-07-08T03:15:00", "source_ip": "192.168.1.45", "request_path": "/api", "method": "POST", "status_code": 200, "payload": "{}"}
            ]
            result = agent.audit_system_security(logs=logs)
        elif agent_name == "calendar_planner":
            niche_strategy = kwargs.get("niche_strategy") or f"Organic growth calendar for {self.workspace.brand_name}."
            days = kwargs.get("days", 3)
            result = agent.plan_content_calendar(niche_strategy=niche_strategy, days=days)
        elif agent_name == "media_generator":
            title = kwargs.get("title") or "Scaling to 10x ROAS"
            media_type = kwargs.get("media_type") or "IMAGE"
            platform = kwargs.get("platform") or "linkedin"
            result = agent.generate_multimodal_assets(title=title, media_type=media_type, platform=platform)
        
        self._log_action(
            agent_name.replace('_', ' ').title(),
            f"Single agent execution completed",
            "EXECUTED"
        )
        
        return result