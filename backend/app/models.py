"""
Database Models for Nexus AI
Uses SQLAlchemy 2.0 with async PostgreSQL
"""
from sqlalchemy import (
    Column, String, Boolean, DateTime, Enum, JSON, Integer, Float,
    ForeignKey, Text, Date, func
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum
import uuid

Base = declarative_base()


# ============================================================================
# ENUMS (Aligned with 001_initial.py database migration)
# ============================================================================

class TenantType(str, enum.Enum):
    AGENCY = "agency"
    SAAS_SUBSCRIBER = "saas_subscriber"


class IntegrationPlatform(str, enum.Enum):
    META = "meta"
    GOOGLE = "google"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"
    PINTEREST = "pinterest"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


# ============================================================================
# MODELS
# ============================================================================

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String(64), primary_key=True, default=lambda: f"t_{uuid.uuid4().hex[:14]}")
    company_name = Column(String(255), nullable=False, unique=True, index=True)
    tenant_type = Column(Enum(TenantType), default=TenantType.SAAS_SUBSCRIBER, nullable=False, index=True)
    stripe_customer_id = Column(String(255), nullable=True)
    billing_plan = Column(String(50), default="professional", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    workspaces = relationship("ClientWorkspace", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    
    id = Column(String(64), primary_key=True, default=lambda: f"u_{uuid.uuid4().hex[:14]}")
    tenant_id = Column(String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(512), nullable=False)
    is_global_admin = Column(Boolean, default=False, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")


class ClientWorkspace(Base):
    __tablename__ = "client_workspaces"
    
    id = Column(String(64), primary_key=True, default=lambda: f"w_{uuid.uuid4().hex[:14]}")
    tenant_id = Column(String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    brand_name = Column(String(255), nullable=False)
    brand_voice_profile = Column(Text, nullable=True)
    autopilot_enabled = Column(Boolean, default=False, nullable=False)
    monthly_budget_cap = Column(Integer, default=0, nullable=False)
    roas_threshold = Column(Float, default=2.0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="workspaces")
    integrations = relationship("SecureIntegration", back_populates="workspace", cascade="all, delete-orphan")
    action_logs = relationship("AgentActionLog", back_populates="workspace", cascade="all, delete-orphan")
    approval_queues = relationship("ApprovalQueue", back_populates="workspace", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="workspace", cascade="all, delete-orphan")
    calendar_items = relationship("ContentCalendarItem", back_populates="workspace", cascade="all, delete-orphan")



class SecureIntegration(Base):
    __tablename__ = "secure_integrations"
    
    id = Column(String(128), primary_key=True, default=lambda: f"int_{uuid.uuid4().hex[:20]}")
    workspace_id = Column(String(64), ForeignKey("client_workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(Enum(IntegrationPlatform), nullable=False, index=True)
    
    # Credentials (Stored encrypted at rest)
    encrypted_access_token = Column(Text, nullable=False)
    encrypted_refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    external_account_id = Column(String(255), nullable=False)
    external_account_name = Column(String(255), nullable=True)
    scopes = Column(Text, nullable=True)
    is_valid = Column(Boolean, default=True, nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    workspace = relationship("ClientWorkspace", back_populates="integrations")


class AgentActionLog(Base):
    __tablename__ = "agent_action_logs"
    
    id = Column(String(128), primary_key=True, default=lambda: f"log_{uuid.uuid4().hex[:20]}")
    workspace_id = Column(String(64), ForeignKey("client_workspaces.id", ondelete="CASCADE"), nullable=True, index=True)
    agent_persona = Column(String(100), nullable=False, index=True)
    action_summary = Column(String(1000), nullable=False)
    detailed_reasoning = Column(Text, nullable=True)
    thinking_trace = Column(Text, nullable=True)
    status = Column(String(50), default="EXECUTED", nullable=False, index=True)
    tokens_used = Column(Integer, default=0, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    workspace = relationship("ClientWorkspace", back_populates="action_logs")


class ApprovalQueue(Base):
    __tablename__ = "approval_queue"
    
    id = Column(String(128), primary_key=True, default=lambda: f"appr_{uuid.uuid4().hex[:20]}")
    workspace_id = Column(String(64), ForeignKey("client_workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_persona = Column(String(100), nullable=False, index=True)
    action_type = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False)
    reasoning = Column(Text, nullable=True)
    risk_score = Column(Integer, default=30, nullable=False)
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False, index=True)
    reviewed_by = Column(String(64), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    workspace = relationship("ClientWorkspace", back_populates="approval_queues")


class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(String(128), primary_key=True, default=lambda: f"camp_{uuid.uuid4().hex[:20]}")
    workspace_id = Column(String(64), ForeignKey("client_workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(Enum(IntegrationPlatform), nullable=False, index=True)
    external_id = Column(String(255), nullable=False, index=True)
    name = Column(String(500), nullable=False)
    objective = Column(String(100), nullable=True)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False, index=True)
    daily_budget_cents = Column(Integer, default=0, nullable=False)
    lifetime_budget_cents = Column(Integer, nullable=True)
    total_spend_cents = Column(Integer, default=0, nullable=False)
    total_revenue_cents = Column(Integer, default=0, nullable=False)
    targeting_config = Column(JSON, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    workspace = relationship("ClientWorkspace", back_populates="campaigns")
    metrics = relationship("CampaignMetric", back_populates="campaign", cascade="all, delete-orphan")


class CampaignMetric(Base):
    __tablename__ = "campaign_metrics"
    
    id = Column(String(128), primary_key=True, default=lambda: f"metr_{uuid.uuid4().hex[:20]}")
    campaign_id = Column(String(128), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    impressions = Column(Integer, default=0, nullable=False)
    clicks = Column(Integer, default=0, nullable=False)
    spend_cents = Column(Integer, default=0, nullable=False)
    conversions = Column(Integer, default=0, nullable=False)
    revenue_cents = Column(Integer, default=0, nullable=False)
    roas_basis_points = Column(Integer, default=0, nullable=False)
    ctr_basis_points = Column(Integer, default=0, nullable=False)
    cpa_cents = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="metrics")


class Session(Base):
    __tablename__ = "sessions"
    
    token = Column(String(512), primary_key=True, index=True, unique=True)
    user_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    role = Column(String(50), default="client", nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(64), primary_key=True, default=lambda: f"aud_{uuid.uuid4().hex[:14]}")
    user_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    tenant_id = Column(String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False)  # "user", "workspace", "integration"
    resource_id = Column(String(64), nullable=False)
    
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(100), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class PlanConfig(Base):
    __tablename__ = "plan_configs"
    
    id = Column(String(64), primary_key=True)  # 'starter', 'professional', or 'agency'
    name = Column(String(100), nullable=False)  # 'Starter', 'Pro', 'Business'
    price = Column(String(100), nullable=False)  # e.g., '₦0', '₦99K', '₦299K'
    period = Column(String(50), nullable=False)  # 'forever' or 'month'
    max_workspaces = Column(Integer, default=1)  # -1 represents unlimited
    max_agents = Column(Integer, default=5)
    ad_budget_cap = Column(Integer, default=500000)  # in Naira, e.g. 500,000 or -1 (unlimited)
    is_published = Column(Boolean, default=True, nullable=False, server_default="1")
    
    # Feature capabilities (Toggles)
    has_basic_analytics = Column(Boolean, default=True)
    has_advanced_analytics = Column(Boolean, default=False)
    has_priority_support = Column(Boolean, default=False)
    has_team_members = Column(Boolean, default=False)
    has_white_label_reports = Column(Boolean, default=False)
    has_dedicated_manager = Column(Boolean, default=False)
    
    # Navigation/Page access permissions
    can_access_ab_testing = Column(Boolean, default=False)
    can_access_audit_log = Column(Boolean, default=False)
    can_access_content_studio = Column(Boolean, default=True)
    can_access_integrations = Column(Boolean, default=True)
    can_access_team = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WorkspaceIntegrationConfig(Base):
    __tablename__ = "workspace_integration_configs"
    
    id = Column(String(128), primary_key=True, default=lambda: f"wic_{uuid.uuid4().hex[:20]}")
    workspace_id = Column(String(64), ForeignKey("client_workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(Enum(IntegrationPlatform), nullable=False, index=True)
    
    client_id = Column(String(255), nullable=False)
    encrypted_client_secret = Column(Text, nullable=False)
    redirect_uri = Column(String(512), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SystemIntegrationConfig(Base):
    __tablename__ = "system_integration_configs"
    
    id = Column(String(128), primary_key=True, default=lambda: f"sic_{uuid.uuid4().hex[:20]}")
    platform = Column(Enum(IntegrationPlatform), nullable=False, unique=True, index=True)
    
    client_id = Column(String(255), nullable=False)
    encrypted_client_secret = Column(Text, nullable=False)
    redirect_uri = Column(String(512), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ContentCalendarItem(Base):
    __tablename__ = "content_calendar_items"
    
    id = Column(String(128), primary_key=True, default=lambda: f"cal_{uuid.uuid4().hex[:20]}")
    workspace_id = Column(String(64), ForeignKey("client_workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(Enum(IntegrationPlatform), nullable=False, index=True)
    scheduled_time = Column(DateTime(timezone=True), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    content_draft = Column(Text, nullable=False)
    media_type = Column(String(50), default="TEXT", nullable=False)  # TEXT, IMAGE, AUDIO, VIDEO
    media_generation_prompt = Column(Text, nullable=True)
    media_url = Column(Text, nullable=True)
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    workspace = relationship("ClientWorkspace", back_populates="calendar_items")



