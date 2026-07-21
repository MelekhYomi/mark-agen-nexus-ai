"""
Tests for API endpoints.
Tests all major API routes including dashboard, content, campaigns, billing, and admin.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestDashboardEndpoints:
    """Tests for dashboard endpoints."""
    
    def test_list_workspaces(self, client, auth_headers, test_workspace):
        """Test listing workspaces."""
        response = client.get(
            "/api/v1/dashboard/workspaces",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "workspaces" in data
        assert len(data["workspaces"]) > 0
    
    def test_get_workspace_summary(self, client, auth_headers, test_workspace):
        """Test getting workspace summary."""
        response = client.get(
            "/api/v1/dashboard/summary",
            params={"workspace_id": test_workspace.id},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "workspace_id" in data
        assert "total_logs" in data
    
    def test_get_agent_logs(self, client, auth_headers, test_workspace):
        """Test getting agent logs."""
        response = client.get(
            "/api/v1/dashboard/agent-logs",
            params={"workspace_id": test_workspace.id, "limit": 10},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data
    
    def test_get_approvals(self, client, auth_headers, test_workspace):
        """Test getting approvals."""
        response = client.get(
            "/api/v1/dashboard/approvals",
            params={"workspace_id": test_workspace.id},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "approvals" in data
    
    def test_toggle_autopilot(self, client, auth_headers, test_workspace):
        """Test toggling autopilot mode."""
        response = client.post(
            f"/api/v1/dashboard/workspaces/{test_workspace.id}/toggle-autopilot",
            params={"enabled": True},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["autopilot_enabled"] == True
    
    def test_unauthorized_access(self, client):
        """Test unauthorized access to protected endpoints."""
        response = client.get("/api/v1/dashboard/workspaces")
        assert response.status_code == 401


class TestContentEndpoints:
    """Tests for content endpoints."""
    
    def test_generate_content(self, client, auth_headers, test_workspace):
        """Test content generation."""
        with patch('app.agents.social_manager.qwen_client') as mock_qwen:
            mock_qwen.chat_completion = MagicMock(
                return_value={
                    "choices": [{"message": {"content": "Test content"}}],
                    "usage": {"total_tokens": 100}
                }
            )
            
            response = client.post(
                "/api/v1/content/generate",
                params={
                    "workspace_id": test_workspace.id,
                    "topic": "Summer Sale",
                    "platform": "instagram",
                    "num_suggestions": 5
                },
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "suggestions" in data
    
    def test_create_post(self, client, auth_headers, test_workspace):
        """Test creating a post."""
        response = client.post(
            "/api/v1/content/create",
            params={
                "workspace_id": test_workspace.id,
                "platform": "instagram",
                "content": "Test post content"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "post" in data

    def test_db_calendar_endpoints(self, client, auth_headers, test_workspace, db_session):
        """Test database-backed content calendar endpoints (get, update, approve, reject)."""
        from app.models import ContentCalendarItem, ApprovalStatus, IntegrationPlatform
        import datetime
        
        # 1. Insert a dummy calendar item
        item = ContentCalendarItem(
            id="test_cal_01",
            workspace_id=test_workspace.id,
            platform=IntegrationPlatform.LINKEDIN,
            scheduled_time=datetime.datetime.now(datetime.UTC),
            title="Succeeding with Qwen AI",
            content_draft="Draft text content",
            media_type="IMAGE",
            status=ApprovalStatus.PENDING
        )
        db_session.add(item)
        db_session.commit()
        
        # 2. Test GET /calendar/items
        response = client.get(
            "/api/v1/content/calendar/items",
            params={"workspace_id": test_workspace.id},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Succeeding with Qwen AI"
        assert data["items"][0]["status"] == "pending"
        
        # 3. Test PUT /calendar/items/{item_id}
        response = client.put(
            f"/api/v1/content/calendar/items/{item.id}",
            json={
                "title": "Succeeding with Alibaba Qwen AI",
                "content_draft": "Updated draft content",
                "status": "approved"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["item"]["title"] == "Succeeding with Alibaba Qwen AI"
        assert data["item"]["content_draft"] == "Updated draft content"
        assert data["item"]["status"] == "approved"
        
        # 4. Test POST /calendar/items/{item_id}/approve
        response = client.post(
            f"/api/v1/content/calendar/items/{item.id}/approve",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status_value"] == "approved"
        
        # 5. Test POST /calendar/items/{item_id}/reject
        response = client.post(
            f"/api/v1/content/calendar/items/{item.id}/reject",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status_value"] == "rejected"


class TestCampaignEndpoints:
    """Tests for campaign endpoints."""
    
    def test_list_campaigns(self, client, auth_headers, test_workspace):
        """Test listing campaigns."""
        response = client.get(
            "/api/v1/campaigns/list",
            params={"workspace_id": test_workspace.id},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "campaigns" in data
    
    def test_create_campaign(self, client, auth_headers, test_workspace):
        """Test creating a campaign."""
        response = client.post(
            "/api/v1/campaigns/create",
            params={
                "workspace_id": test_workspace.id,
                "platform": "meta",
                "objective": "conversions",
                "budget": 500
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "campaign" in data
    
    def test_optimize_campaigns(self, client, auth_headers, test_workspace):
        """Test campaign optimization."""
        with patch('app.agents.ads_manager.qwen_client') as mock_qwen:
            mock_qwen.chat_completion = MagicMock(
                return_value={
                    "choices": [{"message": {"content": "Optimization recommendations"}}],
                    "usage": {"total_tokens": 200}
                }
            )
            
            response = client.post(
                "/api/v1/campaigns/optimize",
                params={"workspace_id": test_workspace.id},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "optimizations" in data


class TestBillingEndpoints:
    """Tests for billing endpoints."""
    
    def test_get_subscription(self, client, auth_headers):
        """Test getting subscription info."""
        response = client.get(
            "/api/v1/billing/subscription",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "subscription" in data
    
    def test_get_pricing_plans(self, client):
        """Test getting pricing plans."""
        response = client.get("/api/v1/billing/plans")
        
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        assert len(data["plans"]) > 0
    
    def test_create_crypto_charge(self, client, auth_headers):
        """Test creating crypto charge."""
        with patch('app.services.crypto.CryptoPaymentService.create_charge') as mock_charge:
            mock_charge.return_value = {
                "charge_id": "charge-123",
                "hosted_url": "https://commerce.coinbase.com/charges/123",
                "amount": 99.00,
                "currency": "USD"
            }
            
            response = client.post(
                "/api/v1/billing/crypto/charge",
                params={
                    "amount": 99.00,
                    "currency": "USD",
                    "description": "Test payment"
                },
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "charge_id" in data


class TestAdminEndpoints:
    """Tests for admin endpoints."""
    
    def test_system_health(self, client, admin_headers):
        """Test system health endpoint."""
        response = client.get(
            "/api/v1/admin/health",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_list_tenants(self, client, admin_headers, test_tenant):
        """Test listing tenants."""
        response = client.get(
            "/api/v1/admin/tenants",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "tenants" in data
    
    def test_toggle_tenant(self, client, admin_headers, test_tenant):
        """Test toggling tenant status."""
        response = client.post(
            f"/api/v1/admin/tenants/{test_tenant.id}/toggle",
            params={"is_active": False},
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] == False
    
    def test_admin_override(self, client, admin_headers):
        """Test admin override."""
        response = client.post(
            "/api/v1/admin/agents/override",
            params={
                "action": "pause_all",
                "reason": "Test override"
            },
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "pause_all"
    
    def test_get_admin_plans(self, client, admin_headers, db_session):
        """Test getting admin plans list."""
        from app.models import PlanConfig
        plan = PlanConfig(
            id="starter", name="Starter", price="₦0", period="forever",
            max_workspaces=1, max_agents=5, ad_budget_cap=500000
        )
        db_session.add(plan)
        db_session.commit()
        
        response = client.get(
            "/api/v1/admin/plans",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        assert len(data["plans"]) == 1
        assert data["plans"][0]["id"] == "starter"

    def test_update_admin_plan(self, client, admin_headers, db_session):
        """Test updating an admin plan configuration."""
        from app.models import PlanConfig
        plan = PlanConfig(
            id="starter", name="Starter", price="₦0", period="forever",
            max_workspaces=1, max_agents=5, ad_budget_cap=500000,
            can_access_ab_testing=False
        )
        db_session.add(plan)
        db_session.commit()
        
        response = client.put(
            "/api/v1/admin/plans/starter",
            json={"price": "₦10K", "can_access_ab_testing": True},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Verify it was updated in the DB
        db_session.refresh(plan)
        assert plan.price == "₦10K"
        assert plan.can_access_ab_testing is True

    def test_public_plan_capabilities(self, client, db_session):
        """Test getting public plan capabilities."""
        from app.models import PlanConfig
        plan = PlanConfig(
            id="starter", name="Starter", price="₦0", period="forever",
            max_workspaces=1, max_agents=5, ad_budget_cap=500000
        )
        db_session.add(plan)
        db_session.commit()
        
        response = client.get("/api/v1/auth/plan-capabilities")
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        assert "starter" in data["plans"]
        assert data["plans"]["starter"]["name"] == "Starter"

    def test_non_admin_access(self, client, auth_headers):
        """Test non-admin access to admin endpoints."""
        response = client.get(
            "/api/v1/admin/health",
            headers=auth_headers
        )
        
        assert response.status_code == 403

    def test_get_and_post_global_oauth_config(self, client, admin_headers, db_session):
        """Test getting and updating global OAuth configurations."""
        # 1. Retrieve current statuses (all unconfigured initially)
        response = client.get("/api/v1/admin/config/oauth", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        configs = data["configs"]
        google_config = next((c for c in configs if c["platform"] == "google"), None)
        assert google_config is not None
        assert google_config["configured"] is False

        # 2. Save Google OAuth Config
        response = client.post(
            "/api/v1/admin/config/oauth/google",
            json={
                "client_id": "google-test-id",
                "client_secret": "google-test-secret",
                "redirect_uri": "https://example.com/callback/google"
            },
            headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # 3. Retrieve and confirm Google is configured
        response = client.get("/api/v1/admin/config/oauth", headers=admin_headers)
        assert response.status_code == 200
        configs = response.json()["configs"]
        google_config = next((c for c in configs if c["platform"] == "google"), None)
        assert google_config["configured"] is True
        assert google_config["client_id"] == "google-test-id"
        assert google_config["redirect_uri"] == "https://example.com/callback/google"

        # 4. Verify 3-tier credential resolution logic
        from app.integrations.oauth import resolve_credentials
        # Resolve google credentials for any workspace
        cid, secret, ruri = resolve_credentials("any-workspace-id", "google", db_session)
        assert cid == "google-test-id"
        assert secret == "google-test-secret"
        assert ruri == "https://example.com/callback/google"


class TestHealthCheck:
    """Tests for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestWebhookEndpoints:
    """Tests for webhook endpoints."""
    
    def test_stripe_webhook_invalid_signature(self, client):
        """Test Stripe webhook with invalid signature."""
        response = client.post(
            "/api/v1/billing/webhook/stripe",
            content=b'{"test": "data"}',
            headers={"stripe-signature": "invalid"}
        )
        
        assert response.status_code == 400
    
    def test_crypto_webhook_missing_signature(self, client):
        """Test crypto webhook with missing signature."""
        response = client.post(
            "/api/v1/billing/webhook/crypto",
            content=b'{"test": "data"}'
        )
        
        assert response.status_code == 400