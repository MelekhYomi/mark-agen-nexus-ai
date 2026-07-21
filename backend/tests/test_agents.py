"""
Tests for AI agent functionality.
Tests all 5 agents with mocked Qwen API responses.
"""
import pytest
from unittest.mock import patch, MagicMock


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


class TestSocialManagerAgent:
    """Tests for Social Media Manager agent."""
    
    def test_generate_content_suggestions(self, db_session, test_workspace):
        """Test content suggestion generation."""
        from app.agents.social_manager import SocialManagerAgent
        
        agent = SocialManagerAgent(db_session, test_workspace.id)
        
        with patch('app.agents.social_manager.qwen_client') as mock_qwen:
            mock_qwen.chat_completion = MagicMock(
                return_value=MockQwenResponse.create(
                    content='[{"title": "Test Post", "platform": "instagram"}]'
                )
            )
            
            result = agent.generate_content_suggestions(num_suggestions=5)
            
            assert "suggestions" in result
            assert "tokens_used" in result
            assert result["tokens_used"] == 100
    
    def test_create_post(self, db_session, test_workspace):
        """Test post creation."""
        from app.agents.social_manager import SocialManagerAgent
        
        agent = SocialManagerAgent(db_session, test_workspace.id)
        
        result = agent.create_post(
            platform="instagram",
            content="Test content",
            media_urls=["https://example.com/image.jpg"]
        )
        
        assert "post_id" in result
        assert result["platform"] == "instagram"
        assert result["status"] == "draft"
    
    def test_generate_hashtags(self, db_session, test_workspace):
        """Test hashtag generation."""
        from app.agents.social_manager import SocialManagerAgent
        
        agent = SocialManagerAgent(db_session, test_workspace.id)
        
        with patch('app.agents.social_manager.qwen_client') as mock_qwen:
            mock_qwen.chat_completion = MagicMock(
                return_value=MockQwenResponse.create(
                    content="#test, #marketing, #social"
                )
            )
            
            hashtags = agent.generate_hashtags(
                topic="marketing",
                platform="instagram",
                count=10
            )
            
            assert isinstance(hashtags, list)


class TestDigitalMarketerAgent:
    """Tests for Digital Marketer agent."""
    
    def test_develop_strategy(self, db_session, test_workspace):
        """Test strategy development."""
        from app.agents.digital_marketer import DigitalMarketerAgent
        
        agent = DigitalMarketerAgent(db_session, test_workspace.id)
        
        with patch('app.agents.digital_marketer.qwen_client') as mock_qwen:
            mock_qwen.chat_completion = MagicMock(
                return_value=MockQwenResponse.create(
                    content='{"strategy": "Focus on social media"}'
                )
            )
            
            result = agent.develop_strategy(focus_area="growth")
            
            assert "strategy" in result
            assert result["focus_area"] == "growth"
    
    def test_analyze_competitors(self, db_session, test_workspace):
        """Test competitor analysis."""
        from app.agents.digital_marketer import DigitalMarketerAgent
        
        agent = DigitalMarketerAgent(db_session, test_workspace.id)
        
        with patch('app.agents.digital_marketer.qwen_client') as mock_qwen:
            mock_qwen.chat_completion = MagicMock(
                return_value=MockQwenResponse.create(
                    content='{"insights": "Competitor A is strong in SEO"}'
                )
            )
            
            result = agent.analyze_competitors(
                competitors=["Competitor A", "Competitor B"]
            )
            
            assert "competitors_analyzed" in result
            assert result["competitors_analyzed"] == 2


class TestAdsManagerAgent:
    """Tests for Ads Manager agent."""
    
    def test_optimize_campaigns(self, db_session, test_workspace):
        """Test campaign optimization."""
        from app.agents.ads_manager import AdsManagerAgent
        
        agent = AdsManagerAgent(db_session, test_workspace.id)
        
        with patch('app.agents.ads_manager.qwen_client') as mock_qwen:
            mock_qwen.chat_completion = MagicMock(
                return_value=MockQwenResponse.create(
                    content='[{"action": "pause_campaign", "campaign_id": "camp-1"}]'
                )
            )
            
            result = agent.optimize_campaigns()
            
            assert "optimizations" in result
            assert "num_recommendations" in result
    
    def test_create_campaign(self, db_session, test_workspace):
        """Test campaign creation."""
        from app.agents.ads_manager import AdsManagerAgent
        
        agent = AdsManagerAgent(db_session, test_workspace.id)
        
        result = agent.create_campaign(
            platform="meta",
            objective="conversions",
            budget=500,
            targeting={"age": "25-45"}
        )
        
        assert "campaign_id" in result
        assert result["platform"] == "meta"
        assert result["status"] == "draft"
    
    def test_adjust_budget(self, db_session, test_workspace):
        """Test budget adjustment."""
        from app.agents.ads_manager import AdsManagerAgent
        
        agent = AdsManagerAgent(db_session, test_workspace.id)
        
        result = agent.adjust_budget(
            campaign_id="camp-123",
            new_budget=750,
            reason="High ROAS"
        )
        
        assert result["new_budget"] == 750
        assert result["requires_approval"] == True
    
    def test_calculate_roas(self, db_session, test_workspace):
        """Test ROAS calculation."""
        from app.agents.ads_manager import AdsManagerAgent
        
        agent = AdsManagerAgent(db_session, test_workspace.id)
        
        roas = agent.calculate_roas(spend=1000, revenue=3500)
        assert roas == 3.5
        
        roas_zero = agent.calculate_roas(spend=0, revenue=1000)
        assert roas_zero == 0.0


class TestSEOExpertAgent:
    """Tests for SEO Expert agent."""
    
    def test_improve_rankings(self, db_session, test_workspace):
        """Test SEO improvement recommendations."""
        from app.agents.seo_expert import SEOExpertAgent
        
        agent = SEOExpertAgent(db_session, test_workspace.id)
        
        with patch('app.agents.seo_expert.qwen_client') as mock_qwen:
            mock_qwen.chat_completion = MagicMock(
                return_value=MockQwenResponse.create(
                    content='{"recommendations": ["Improve meta tags"]}'
                )
            )
            
            result = agent.improve_rankings()
            
            assert "recommendations" in result
            assert "priority_actions" in result
    
    def test_keyword_research(self, db_session, test_workspace):
        """Test keyword research."""
        from app.agents.seo_expert import SEOExpertAgent
        
        agent = SEOExpertAgent(db_session, test_workspace.id)
        
        with patch('app.agents.seo_expert.qwen_client') as mock_qwen:
            mock_qwen.chat_completion = MagicMock(
                return_value=MockQwenResponse.create(
                    content='[{"keyword": "marketing", "volume": 10000}]'
                )
            )
            
            result = agent.keyword_research(
                niche="digital marketing",
                seed_keywords=["marketing", "seo"]
            )
            
            assert "keywords" in result
            assert result["niche"] == "digital marketing"


class TestAnalyticsAgent:
    """Tests for Analytics agent."""
    
    def test_analyze_performance(self, db_session, test_workspace):
        """Test performance analysis."""
        from app.agents.analytics import AnalyticsAgent
        
        agent = AnalyticsAgent(db_session, test_workspace.id)
        
        with patch('app.agents.analytics.qwen_client') as mock_qwen:
            mock_qwen.chat_completion = MagicMock(
                return_value=MockQwenResponse.create(
                    content='{"insights": "Traffic increased 20%"}'
                )
            )
            
            result = agent.analyze_performance(period="last_30_days")
            
            assert "insights" in result
            assert result["period"] == "last_30_days"
    
    def test_generate_report(self, db_session, test_workspace):
        """Test report generation."""
        from app.agents.analytics import AnalyticsAgent
        
        agent = AnalyticsAgent(db_session, test_workspace.id)
        
        with patch('app.agents.analytics.qwen_client') as mock_qwen:
            mock_qwen.chat_completion = MagicMock(
                return_value=MockQwenResponse.create(
                    content='{"summary": "Good performance"}'
                )
            )
            
            result = agent.generate_report(period="weekly")
            
            assert "report" in result
            assert result["period"] == "weekly"
    
    def test_forecast_growth(self, db_session, test_workspace):
        """Test growth forecasting."""
        from app.agents.analytics import AnalyticsAgent
        
        agent = AnalyticsAgent(db_session, test_workspace.id)
        
        with patch('app.agents.analytics.qwen_client') as mock_qwen:
            mock_qwen.chat_completion = MagicMock(
                return_value=MockQwenResponse.create(
                    content='{"forecast": "10% growth expected"}'
                )
            )
            
            result = agent.forecast_growth(months=3)
            
            assert "forecast" in result
            assert result["months"] == 3


class TestAgentOrchestrator:
    """Tests for agent orchestrator."""
    
    def test_run_full_cycle(self, db_session, test_workspace):
        """Test running full agent cycle."""
        from app.agents.orchestrator import AgentOrchestrator
        
        orchestrator = AgentOrchestrator(db_session, test_workspace.id)
        
        with patch.object(orchestrator.analytics, 'analyze_performance') as mock_analytics, \
             patch.object(orchestrator.social_manager, 'generate_content_suggestions') as mock_social, \
             patch.object(orchestrator.digital_marketer, 'develop_strategy') as mock_marketer, \
             patch.object(orchestrator.ads_manager, 'optimize_campaigns') as mock_ads, \
             patch.object(orchestrator.seo_expert, 'improve_rankings') as mock_seo:
            
            mock_analytics.return_value = {"insights": "test", "tokens_used": 100}
            mock_social.return_value = {"suggestions": [], "tokens_used": 100}
            mock_marketer.return_value = {"strategy": "test", "tokens_used": 100}
            mock_ads.return_value = {"optimizations": [], "tokens_used": 100}
            mock_seo.return_value = {"recommendations": [], "tokens_used": 100}
            
            result = orchestrator.run_full_cycle()
            
            assert "agents" in result
            assert "summary" in result
            assert result["workspace_id"] == test_workspace.id
    
    def test_run_single_agent(self, db_session, test_workspace):
        """Test running a single agent."""
        from app.agents.orchestrator import AgentOrchestrator
        
        orchestrator = AgentOrchestrator(db_session, test_workspace.id)
        
        with patch.object(orchestrator.analytics, 'analyze_performance') as mock_analytics:
            mock_analytics.return_value = {"insights": "test", "tokens_used": 100}
            
            result = orchestrator.run_single_agent("analytics")
            
            assert "insights" in result