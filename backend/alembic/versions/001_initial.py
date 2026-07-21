"""Initial schema - Create all Nexus AI tables

Revision ID: 001
Revises: 
Create Date: 2026-06-23 00:00:00.000000

This migration creates the complete database schema for Nexus AI including:
- Tenants (multi-tenant isolation)
- Users (authentication & authorization)
- Client Workspaces (brand management)
- Secure Integrations (OAuth tokens)
- Agent Action Logs (audit trail)
- Approval Queue (human-in-the-loop)
- Campaigns (ad campaign tracking)
- Campaign Metrics (performance data)
- Sessions (JWT session management)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all Nexus AI tables with proper indexes and constraints."""
    
    # ========================================================================
    # ENUM TYPES
    # ========================================================================
    
    # Tenant types
    op.execute("""
        CREATE TYPE tenant_type AS ENUM (
            'agency',
            'saas_subscriber'
        )
    """)
    
    # Integration platforms
    op.execute("""
        CREATE TYPE integration_platform AS ENUM (
            'meta',
            'google',
            'tiktok',
            'twitter',
            'linkedin',
            'youtube',
            'pinterest'
        )
    """)
    
    # Approval statuses
    op.execute("""
        CREATE TYPE approval_status AS ENUM (
            'pending',
            'approved',
            'rejected',
            'failed'
        )
    """)
    
    # Campaign statuses
    op.execute("""
        CREATE TYPE campaign_status AS ENUM (
            'draft',
            'active',
            'paused',
            'completed',
            'archived'
        )
    """)
    
    # ========================================================================
    # TENANTS TABLE
    # ========================================================================
    op.create_table(
        'tenants',
        sa.Column('id', sa.String(length=64), primary_key=True, nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('tenant_type', sa.Enum('agency', 'saas_subscriber', name='tenant_type'), nullable=False, server_default='saas_subscriber'),
        sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    op.create_index('ix_tenants_id', 'tenants', ['id'], unique=False)
    op.create_index('ix_tenants_tenant_type', 'tenants', ['tenant_type'], unique=False)
    op.create_index('ix_tenants_is_active', 'tenants', ['is_active'], unique=False)
    
    # ========================================================================
    # USERS TABLE
    # ========================================================================
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=64), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=64), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=512), nullable=False),
        sa.Column('is_global_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_is_global_admin', 'users', ['is_global_admin'], unique=False)
    
    # ========================================================================
    # CLIENT WORKSPACES TABLE
    # ========================================================================
    op.create_table(
        'client_workspaces',
        sa.Column('id', sa.String(length=64), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=64), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('brand_name', sa.String(length=255), nullable=False),
        sa.Column('brand_voice_profile', sa.Text(), nullable=True),
        sa.Column('autopilot_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('monthly_budget_cap', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('roas_threshold', sa.Float(), nullable=False, server_default='2.0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    op.create_index('ix_client_workspaces_id', 'client_workspaces', ['id'], unique=False)
    op.create_index('ix_client_workspaces_tenant_id', 'client_workspaces', ['tenant_id'], unique=False)
    op.create_index('ix_client_workspaces_is_active', 'client_workspaces', ['is_active'], unique=False)
    
    # ========================================================================
    # SECURE INTEGRATIONS TABLE (OAuth tokens)
    # ========================================================================
    op.create_table(
        'secure_integrations',
        sa.Column('id', sa.String(length=128), primary_key=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=64), sa.ForeignKey('client_workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('platform', sa.Enum('meta', 'google', 'tiktok', 'twitter', 'linkedin', 'youtube', 'pinterest', name='integration_platform'), nullable=False),
        sa.Column('encrypted_access_token', sa.Text(), nullable=False),
        sa.Column('encrypted_refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('external_account_id', sa.String(length=255), nullable=False),
        sa.Column('external_account_name', sa.String(length=255), nullable=True),
        sa.Column('scopes', sa.Text(), nullable=True),
        sa.Column('is_valid', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    op.create_index('ix_secure_integrations_id', 'secure_integrations', ['id'], unique=False)
    op.create_index('ix_secure_integrations_workspace_id', 'secure_integrations', ['workspace_id'], unique=False)
    op.create_index('ix_secure_integrations_platform', 'secure_integrations', ['platform'], unique=False)
    op.create_index('ix_secure_integrations_is_valid', 'secure_integrations', ['is_valid'], unique=False)
    op.create_index('ix_secure_integrations_token_expires', 'secure_integrations', ['token_expires_at'], unique=False)
    
    # ========================================================================
    # AGENT ACTION LOGS TABLE
    # ========================================================================
    op.create_table(
        'agent_action_logs',
        sa.Column('id', sa.String(length=128), primary_key=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=64), sa.ForeignKey('client_workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_persona', sa.String(length=100), nullable=False),
        sa.Column('action_summary', sa.String(length=1000), nullable=False),
        sa.Column('detailed_reasoning', sa.Text(), nullable=True),
        sa.Column('thinking_trace', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='EXECUTED'),
        sa.Column('tokens_used', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    op.create_index('ix_agent_action_logs_id', 'agent_action_logs', ['id'], unique=False)
    op.create_index('ix_agent_action_logs_workspace_id', 'agent_action_logs', ['workspace_id'], unique=False)
    op.create_index('ix_agent_action_logs_agent_persona', 'agent_action_logs', ['agent_persona'], unique=False)
    op.create_index('ix_agent_action_logs_status', 'agent_action_logs', ['status'], unique=False)
    op.create_index('ix_agent_action_logs_created_at', 'agent_action_logs', ['created_at'], unique=False)
    
    # Composite index for common queries
    op.create_index(
        'ix_agent_action_logs_workspace_created',
        'agent_action_logs',
        ['workspace_id', 'created_at'],
        unique=False
    )
    
    # ========================================================================
    # APPROVAL QUEUE TABLE
    # ========================================================================
    op.create_table(
        'approval_queue',
        sa.Column('id', sa.String(length=128), primary_key=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=64), sa.ForeignKey('client_workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_persona', sa.String(length=100), nullable=False),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('risk_score', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', 'failed', name='approval_status'), nullable=False, server_default='pending'),
        sa.Column('reviewed_by', sa.String(length=64), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    op.create_index('ix_approval_queue_id', 'approval_queue', ['id'], unique=False)
    op.create_index('ix_approval_queue_workspace_id', 'approval_queue', ['workspace_id'], unique=False)
    op.create_index('ix_approval_queue_status', 'approval_queue', ['status'], unique=False)
    op.create_index('ix_approval_queue_agent_persona', 'approval_queue', ['agent_persona'], unique=False)
    op.create_index('ix_approval_queue_created_at', 'approval_queue', ['created_at'], unique=False)
    
    # Composite index for pending approvals by workspace
    op.create_index(
        'ix_approval_queue_workspace_status',
        'approval_queue',
        ['workspace_id', 'status'],
        unique=False
    )
    
    # ========================================================================
    # CAMPAIGNS TABLE
    # ========================================================================
    op.create_table(
        'campaigns',
        sa.Column('id', sa.String(length=128), primary_key=True, nullable=False),
        sa.Column('workspace_id', sa.String(length=64), sa.ForeignKey('client_workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('platform', sa.Enum('meta', 'google', 'tiktok', 'twitter', 'linkedin', 'youtube', 'pinterest', name='integration_platform'), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('objective', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('draft', 'active', 'paused', 'completed', 'archived', name='campaign_status'), nullable=False, server_default='draft'),
        sa.Column('daily_budget_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('lifetime_budget_cents', sa.Integer(), nullable=True),
        sa.Column('total_spend_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_revenue_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('targeting_config', sa.JSON(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    op.create_index('ix_campaigns_id', 'campaigns', ['id'], unique=False)
    op.create_index('ix_campaigns_workspace_id', 'campaigns', ['workspace_id'], unique=False)
    op.create_index('ix_campaigns_platform', 'campaigns', ['platform'], unique=False)
    op.create_index('ix_campaigns_external_id', 'campaigns', ['external_id'], unique=False)
    op.create_index('ix_campaigns_status', 'campaigns', ['status'], unique=False)
    
    # Composite index for active campaigns by workspace
    op.create_index(
        'ix_campaigns_workspace_status',
        'campaigns',
        ['workspace_id', 'status'],
        unique=False
    )
    
    # ========================================================================
    # CAMPAIGN METRICS TABLE
    # ========================================================================
    op.create_table(
        'campaign_metrics',
        sa.Column('id', sa.String(length=128), primary_key=True, nullable=False),
        sa.Column('campaign_id', sa.String(length=128), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('impressions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('clicks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('spend_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('conversions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('revenue_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('roas_basis_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ctr_basis_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cpa_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    op.create_index('ix_campaign_metrics_id', 'campaign_metrics', ['id'], unique=False)
    op.create_index('ix_campaign_metrics_campaign_id', 'campaign_metrics', ['campaign_id'], unique=False)
    op.create_index('ix_campaign_metrics_date', 'campaign_metrics', ['date'], unique=False)
    
    # Unique constraint: one metrics row per campaign per day
    op.create_unique_constraint(
        'uq_campaign_metrics_campaign_date',
        'campaign_metrics',
        ['campaign_id', 'date']
    )
    
    # ========================================================================
    # SESSIONS TABLE
    # ========================================================================
    op.create_table(
        'sessions',
        sa.Column('token', sa.String(length=512), primary_key=True, nullable=False),
        sa.Column('user_id', sa.String(length=64), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='client'),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    
    op.create_index('ix_sessions_token', 'sessions', ['token'], unique=True)
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'], unique=False)
    op.create_index('ix_sessions_tenant_id', 'sessions', ['tenant_id'], unique=False)
    op.create_index('ix_sessions_expires_at', 'sessions', ['expires_at'], unique=False)
    
    # ========================================================================
    # SEED DATA (Optional - uncomment if needed)
    # ========================================================================
    # Uncomment the following to seed initial data:
    #
    # op.execute("""
    #     INSERT INTO tenants (id, company_name, tenant_type, is_active)
    #     VALUES ('t_default_admin', 'Platform Admin', 'agency', true)
    # """)
    #
    # op.execute("""
    #     INSERT INTO users (id, tenant_id, email, name, hashed_password, is_global_admin)
    #     VALUES ('u_default_admin', 't_default_admin', 'admin@platform.com', 'Alex Chen', 
    #             '$2b$12$LJ3m4ys1Lg0KqZqZqZqZqO', true)
    # """)


def downgrade() -> None:
    """Drop all Nexus AI tables in reverse order of creation."""
    
    # Drop tables (order matters due to foreign keys)
    op.drop_table('sessions')
    op.drop_table('campaign_metrics')
    op.drop_table('campaigns')
    op.drop_table('approval_queue')
    op.drop_table('agent_action_logs')
    op.drop_table('secure_integrations')
    op.drop_table('client_workspaces')
    op.drop_table('users')
    op.drop_table('tenants')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS campaign_status")
    op.execute("DROP TYPE IF EXISTS approval_status")
    op.execute("DROP TYPE IF EXISTS integration_platform")
    op.execute("DROP TYPE IF EXISTS tenant_type")