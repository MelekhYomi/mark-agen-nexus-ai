"""
Tests for newly added Qwen-powered expansion agents and their Orchestrator integration.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.agents.brand_guardian import BrandGuardianAgent
from app.agents.conversion_optimizer import ConversionOptimizerAgent
from app.agents.community_engagement import CommunityEngagementAgent
from app.agents.market_intelligence import MarketIntelligenceAgent
from app.agents.dynamic_cfo import DynamicCFOAgent
from app.agents.security_sre import SecuritySREAgent
from app.agents.calendar_planner import CalendarPlannerAgent
from app.agents.media_generator import MediaGeneratorAgent
from app.agents.orchestrator import AgentOrchestrator


class MockQwenResponse:
    """Mock Qwen API response."""
    
    @staticmethod
    def create(content="Mock response", tokens=100):
        return {
            "choices": [
                {
                    "message": {
                        "content": content,
                        "reasoning_content": "Mock reasoning trace"
                    }
                }
            ],
            "usage": {
                "total_tokens": tokens
            }
        }


def test_brand_guardian_agent(db_session, test_workspace):
    """Test Brand & Compliance Guardian Agent."""
    agent = BrandGuardianAgent(db_session, test_workspace.id)
    
    with patch('app.agents.brand_guardian.qwen_client') as mock_qwen:
        mock_json = '{"approved": true, "risk_score": 0.1, "compliance_score": 0.9, "brand_voice_alignment": 0.95, "issues_found": [], "suggested_rewrite": "Perfect post!"}'
        mock_qwen.chat_completion = MagicMock(return_value=MockQwenResponse.create(content=mock_json))
        
        result = agent.audit_content(content="Great new launch!", platform="twitter")
        
        assert result["status"] == "success"
        assert result["audit"]["approved"] is True
        assert result["audit"]["risk_score"] == 0.1
        assert "suggested_rewrite" in result["audit"]


def test_conversion_optimizer_agent(db_session, test_workspace):
    """Test Conversion & A/B Optimizer Agent."""
    agent = ConversionOptimizerAgent(db_session, test_workspace.id)
    
    with patch('app.agents.conversion_optimizer.qwen_client') as mock_qwen:
        mock_json = '{"campaign_evaluations": [], "ab_test_suggestions": [], "predicted_roi_uplift": 18.5}'
        mock_qwen.chat_completion = MagicMock(return_value=MockQwenResponse.create(content=mock_json))
        
        result = agent.optimize_conversion_funnels(campaigns_data=[])
        
        assert result["status"] == "success"
        assert result["optimizations"]["predicted_roi_uplift"] == 18.5


def test_community_engagement_agent(db_session, test_workspace):
    """Test Community Engagement & Sentiment Agent."""
    agent = CommunityEngagementAgent(db_session, test_workspace.id)
    
    with patch('app.agents.community_engagement.qwen_client') as mock_qwen:
        mock_json = '{"overall_sentiment_score": 0.8, "urgency_count": 0, "processed_interactions": []}'
        mock_qwen.chat_completion = MagicMock(return_value=MockQwenResponse.create(content=mock_json))
        
        result = agent.process_engagement_stream(interactions=[])
        
        assert result["status"] == "success"
        assert result["engagement"]["overall_sentiment_score"] == 0.8


def test_market_intelligence_agent(db_session, test_workspace):
    """Test Market Intelligence & Scraping Agent."""
    agent = MarketIntelligenceAgent(db_session, test_workspace.id)
    
    with patch('app.agents.market_intelligence.qwen_client') as mock_qwen:
        mock_json = '{"market_niche": "AI Marketing", "top_competitors": [], "trending_hashtags_and_keywords": [], "viral_triggers": [], "strategic_gaps": []}'
        mock_qwen.chat_completion = MagicMock(return_value=MockQwenResponse.create(content=mock_json))
        
        result = agent.generate_competitor_brief(industry_niche="AI Marketing")
        
        assert result["status"] == "success"
        assert result["brief"]["market_niche"] == "AI Marketing"


def test_dynamic_cfo_agent(db_session, test_workspace):
    """Test Dynamic CFO & Subscription Optimizer Agent."""
    agent = DynamicCFOAgent(db_session, test_workspace.id)
    
    with patch('app.agents.dynamic_cfo.qwen_client') as mock_qwen:
        mock_json = '{"billing_health_grade": "A", "churn_risk_percentage": 5.0, "recommended_pricing_tier": "PRO", "optimization_triggers": []}'
        mock_qwen.chat_completion = MagicMock(return_value=MockQwenResponse.create(content=mock_json))
        
        result = agent.analyze_subscription_health(billing_history={}, active_usage={})
        
        assert result["status"] == "success"
        assert result["revenue_optimization"]["billing_health_grade"] == "A"
        assert result["revenue_optimization"]["churn_risk_percentage"] == 5.0


def test_security_sre_agent(db_session, test_workspace):
    """Test SRE & Security Audit Agent."""
    agent = SecuritySREAgent(db_session, test_workspace.id)
    
    with patch('app.agents.security_sre.qwen_client') as mock_qwen:
        mock_json = '{"secure": true, "threat_level": "LOW", "anomalies_detected": [], "auto_mitigation_actions": [], "audit_summary": "System is clean."}'
        mock_qwen.chat_completion = MagicMock(return_value=MockQwenResponse.create(content=mock_json))
        
        result = agent.audit_system_security(logs=[])
        
        assert result["status"] == "success"
        assert result["security_audit"]["secure"] is True
        assert result["security_audit"]["threat_level"] == "LOW"


def test_calendar_planner_agent(db_session, test_workspace):
    """Test Content Calendar & Scheduler Agent."""
    agent = CalendarPlannerAgent(db_session, test_workspace.id)
    
    with patch('app.agents.calendar_planner.qwen_client') as mock_qwen:
        mock_json = '{"niche_strategy": "SaaS B2B strategy", "calendar_items": [{"platform": "linkedin", "relative_day": 1, "hour_of_day": 10, "title": "Post 1", "topic_focus": "Thought Leadership", "media_type": "TEXT", "content_angle": "Discuss swarms."}]}'
        mock_qwen.chat_completion = MagicMock(return_value=MockQwenResponse.create(content=mock_json))
        
        result = agent.plan_content_calendar(niche_strategy="B2B growth", days=1)
        
        assert result["status"] == "success"
        assert result["calendar_items_count"] == 1
        assert result["saved_items"][0]["platform"] == "linkedin"
        assert result["saved_items"][0]["title"] == "Post 1"


def test_media_generator_agent(db_session, test_workspace):
    """Test Media Generator Agent."""
    agent = MediaGeneratorAgent(db_session, test_workspace.id)
    
    with patch('app.agents.media_generator.qwen_client') as mock_qwen:
        mock_json = '{"media_type": "IMAGE", "image_prompt": "Futuristic UI", "graphic_concept": "Sleek slate", "audio_script": null, "video_storyboard": null, "asset_url": "https://oss-eu-central.aliyuncs.com/nexus/1.jpg"}'
        mock_qwen.chat_completion = MagicMock(return_value=MockQwenResponse.create(content=mock_json))
        
        result = agent.generate_multimodal_assets(title="AI Launch", media_type="IMAGE", platform="twitter")
        
        assert result["status"] == "success"
        assert result["media_assets"]["media_type"] == "IMAGE"
        assert result["media_assets"]["asset_url"] == "https://oss-eu-central.aliyuncs.com/nexus/1.jpg"


def test_orchestrator_expansion_full_cycle(db_session, test_workspace):
    """Test that AgentOrchestrator runs all 13 agents in full cycle."""
    orchestrator = AgentOrchestrator(db_session, test_workspace.id)
    
    # Mock chat completions for all agents to ensure fast running
    with patch('app.agents.social_manager.qwen_client') as mock_social, \
         patch('app.agents.digital_marketer.qwen_client') as mock_marketer, \
         patch('app.agents.ads_manager.qwen_client') as mock_ads, \
         patch('app.agents.seo_expert.qwen_client') as mock_seo, \
         patch('app.agents.analytics.qwen_client') as mock_analytics, \
         patch('app.agents.brand_guardian.qwen_client') as mock_brand, \
         patch('app.agents.conversion_optimizer.qwen_client') as mock_conversion, \
         patch('app.agents.community_engagement.qwen_client') as mock_community, \
         patch('app.agents.market_intelligence.qwen_client') as mock_market, \
         patch('app.agents.dynamic_cfo.qwen_client') as mock_cfo, \
         patch('app.agents.security_sre.qwen_client') as mock_sre, \
         patch('app.agents.calendar_planner.qwen_client') as mock_calendar, \
         patch('app.agents.media_generator.qwen_client') as mock_media:
         
        # Set return values for all mocks
        mock_social.chat_completion = MagicMock(return_value=MockQwenResponse.create('[{"title": "Post", "description": "Desc"}]'))
        mock_marketer.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"strategy": "Focus social"}'))
        mock_ads.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"optimizations": []}'))
        mock_seo.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"keywords": []}'))
        mock_analytics.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"insights": []}'))
        mock_brand.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"approved": true, "risk_score": 0.1, "compliance_score": 0.9, "brand_voice_alignment": 0.9, "issues_found": [], "suggested_rewrite": ""}'))
        mock_conversion.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"campaign_evaluations": [], "ab_test_suggestions": [], "predicted_roi_uplift": 10.0}'))
        mock_community.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"overall_sentiment_score": 0.9, "urgency_count": 0, "processed_interactions": []}'))
        mock_market.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"market_niche": "SaaS", "top_competitors": []}'))
        mock_cfo.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"billing_health_grade": "A", "churn_risk_percentage": 2.0}'))
        mock_sre.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"secure": true, "threat_level": "LOW"}'))
        mock_calendar.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"niche_strategy": "SaaS Strategy", "calendar_items": [{"platform": "linkedin", "relative_day": 1, "hour_of_day": 12, "title": "B2B Post", "media_type": "IMAGE", "content_angle": "Angle"}]}'))
        mock_media.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"media_type": "IMAGE", "image_prompt": "Prompt", "graphic_concept": "Concept", "asset_url": "https://oss-eu-central.aliyuncs.com/nexus/1.jpg"}'))
        
        results = orchestrator.run_full_cycle()
        
        # Verify overall structure and execution
        assert "agents" in results
        assert "brand_guardian" in results["agents"]
        assert "conversion_optimizer" in results["agents"]
        assert "community_engagement" in results["agents"]
        assert "market_intelligence" in results["agents"]
        assert "dynamic_cfo" in results["agents"]
        assert "security_sre" in results["agents"]
        assert "calendar_planner" in results["agents"]
        assert "media_generator" in results["agents"]
        
        # Verify no error keys inside any agent's results (indicating all succeeded)
        for agent_key in ["brand_guardian", "conversion_optimizer", "community_engagement", "market_intelligence", "dynamic_cfo", "security_sre", "calendar_planner", "media_generator"]:
            assert "error" not in results["agents"][agent_key]
            
        assert results["summary"]["errors"] == 0
        assert results["summary"]["total_actions"] >= 13


def test_orchestrator_expansion_single_agent(db_session, test_workspace):
    """Test running individual new expansion agents through run_single_agent."""
    orchestrator = AgentOrchestrator(db_session, test_workspace.id)
    
    with patch('app.agents.brand_guardian.qwen_client') as mock_brand, \
         patch('app.agents.conversion_optimizer.qwen_client') as mock_conversion, \
         patch('app.agents.community_engagement.qwen_client') as mock_community, \
         patch('app.agents.market_intelligence.qwen_client') as mock_market, \
         patch('app.agents.dynamic_cfo.qwen_client') as mock_cfo, \
         patch('app.agents.security_sre.qwen_client') as mock_sre, \
         patch('app.agents.calendar_planner.qwen_client') as mock_calendar, \
         patch('app.agents.media_generator.qwen_client') as mock_media:
         
        mock_brand.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"approved": true, "risk_score": 0.1}'))
        mock_conversion.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"predicted_roi_uplift": 10.0}'))
        mock_community.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"overall_sentiment_score": 0.9}'))
        mock_market.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"market_niche": "SaaS"}'))
        mock_cfo.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"billing_health_grade": "A"}'))
        mock_sre.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"secure": true}'))
        mock_calendar.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"niche_strategy": "SaaS Strategy", "calendar_items": [{"platform": "linkedin", "relative_day": 1, "hour_of_day": 12, "title": "B2B Post", "media_type": "IMAGE", "content_angle": "Angle"}]}'))
        mock_media.chat_completion = MagicMock(return_value=MockQwenResponse.create('{"media_type": "IMAGE", "image_prompt": "Prompt", "graphic_concept": "Concept", "asset_url": "https://oss-eu-central.aliyuncs.com/nexus/1.jpg"}'))
        
        # Test brand_guardian
        res = orchestrator.run_single_agent("brand_guardian", content="Test", platform="twitter")
        assert res["status"] == "success"
        
        # Test conversion_optimizer
        res = orchestrator.run_single_agent("conversion_optimizer")
        assert res["status"] == "success"
        
        # Test community_engagement
        res = orchestrator.run_single_agent("community_engagement")
        assert res["status"] == "success"
        
        # Test market_intelligence
        res = orchestrator.run_single_agent("market_intelligence")
        assert res["status"] == "success"
        
        # Test dynamic_cfo
        res = orchestrator.run_single_agent("dynamic_cfo")
        assert res["status"] == "success"
        
        # Test security_sre
        res = orchestrator.run_single_agent("security_sre")
        assert res["status"] == "success"

        # Test calendar_planner
        res = orchestrator.run_single_agent("calendar_planner")
        assert res["status"] == "success"

        # Test media_generator
        res = orchestrator.run_single_agent("media_generator")
        assert res["status"] == "success"
