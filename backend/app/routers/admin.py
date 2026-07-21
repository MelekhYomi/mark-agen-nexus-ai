"""
Admin Router
Provides endpoints for system administration, tenant management, and monitoring.
"""
import logging
from typing import Optional, List, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Tenant, ClientWorkspace, User, AgentActionLog,
    ApprovalQueue, SecureIntegration, PlanConfig, SystemIntegrationConfig, IntegrationPlatform
)
from app.auth.dependencies import require_admin, CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ============================================================================
# SYSTEM HEALTH ENDPOINTS
# ============================================================================

@router.get("/plans")
async def get_plans_list(
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Retrieve all custom pricing plans and feature sets in real time.
    """
    result = db.execute(select(PlanConfig))
    plans = result.scalars().all()
    return {
        "status": "success",
        "plans": [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "period": p.period,
                "max_workspaces": p.max_workspaces,
                "max_agents": p.max_agents,
                "ad_budget_cap": p.ad_budget_cap,
                "is_published": p.is_published,
                "has_basic_analytics": p.has_basic_analytics,
                "has_advanced_analytics": p.has_advanced_analytics,
                "has_priority_support": p.has_priority_support,
                "has_team_members": p.has_team_members,
                "has_white_label_reports": p.has_white_label_reports,
                "has_dedicated_manager": p.has_dedicated_manager,
                "can_access_ab_testing": p.can_access_ab_testing,
                "can_access_audit_log": p.can_access_audit_log,
                "can_access_content_studio": p.can_access_content_studio,
                "can_access_integrations": p.can_access_integrations,
                "can_access_team": p.can_access_team,
            }
            for p in plans
        ]
    }


@router.put("/plans/{plan_id}")
async def update_plan_config(
    plan_id: str,
    payload: Dict,
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update pricing plans, toggle features, or edit access rules dynamically.
    """
    result = db.execute(select(PlanConfig).where(PlanConfig.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Plan configuration not found")
        
    for key, val in payload.items():
        if hasattr(plan, key):
            setattr(plan, key, val)
            
    db.commit()
    return {"status": "success", "message": f"Plan {plan_id} updated successfully"}


@router.post("/plans")
async def create_plan_config(
    payload: Dict,
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new subscription plan dynamically.
    """
    plan_id = payload.get("id")
    if not plan_id:
        raise HTTPException(400, "Plan ID is required")
        
    # Check if plan already exists
    existing = db.execute(select(PlanConfig).where(PlanConfig.id == plan_id))
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Plan with ID '{plan_id}' already exists")
        
    new_plan = PlanConfig(
        id=plan_id,
        name=payload.get("name", "New Plan"),
        price=payload.get("price", "₦0"),
        period=payload.get("period", "month"),
        max_workspaces=payload.get("max_workspaces", 1),
        max_agents=payload.get("max_agents", 5),
        ad_budget_cap=payload.get("ad_budget_cap", 500000),
        is_published=payload.get("is_published", True),
        has_basic_analytics=payload.get("has_basic_analytics", True),
        has_advanced_analytics=payload.get("has_advanced_analytics", False),
        has_priority_support=payload.get("has_priority_support", False),
        has_team_members=payload.get("has_team_members", False),
        has_white_label_reports=payload.get("has_white_label_reports", False),
        has_dedicated_manager=payload.get("has_dedicated_manager", False),
        can_access_ab_testing=payload.get("can_access_ab_testing", False),
        can_access_audit_log=payload.get("can_access_audit_log", False),
        can_access_content_studio=payload.get("can_access_content_studio", True),
        can_access_integrations=payload.get("can_access_integrations", True),
        can_access_team=payload.get("can_access_team", False),
    )
    
    db.add(new_plan)
    db.commit()
    return {"status": "success", "message": f"Plan {plan_id} created successfully", "plan_id": plan_id}


@router.delete("/plans/{plan_id}")
async def delete_plan_config(
    plan_id: str,
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a pricing plan dynamically.
    """
    result = db.execute(select(PlanConfig).where(PlanConfig.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Plan config not found")
        
    # Prevent deleting standard default system plans to avoid breakage
    if plan_id in ["starter", "professional", "agency"]:
        raise HTTPException(400, "Cannot delete default system plans (starter, professional, agency)")
        
    db.delete(plan)
    db.commit()
    return {"status": "success", "message": f"Plan {plan_id} deleted successfully"}



# ============================================================================
# SYSTEM HEALTH ENDPOINTS
# ============================================================================

@router.get("/health")
async def system_health(
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get system health status and metrics.
    """
    tenant_count = db.execute(select(func.count(Tenant.id)))
    workspace_count = db.execute(select(func.count(ClientWorkspace.id)))
    user_count = db.execute(select(func.count(User.id)))
    log_count = db.execute(select(func.count(AgentActionLog.id)))
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "tenants": tenant_count.scalar(),
            "workspaces": workspace_count.scalar(),
            "users": user_count.scalar(),
            "agent_logs": log_count.scalar()
        }
    }


# ============================================================================
# TENANT MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/tenants")
async def list_tenants(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    List all tenants with filtering and pagination.
    """
    query = select(Tenant)
    
    if search:
        query = query.where(Tenant.company_name.ilike(f"%{search}%"))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (db.execute(count_query)).scalar()
    
    # Get paginated results
    query = query.order_by(Tenant.created_at.desc()).offset(offset).limit(limit)
    result = db.execute(query)
    tenants = result.scalars().all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "tenants": [
            {
                "id": t.id,
                "company_name": t.company_name,
                "tenant_type": t.tenant_type.value if hasattr(t.tenant_type, "value") else t.tenant_type,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat() if t.created_at else datetime.utcnow().isoformat()
            }
            for t in tenants
        ]
    }


@router.get("/tenants/{tenant_id}")
async def get_tenant_detail(
    tenant_id: str,
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific tenant.
    """
    result = db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    
    # Get workspace count
    workspace_count = db.execute(
        select(func.count(ClientWorkspace.id))
        .where(ClientWorkspace.tenant_id == tenant_id)
    )
    
    # Get user count
    user_count = db.execute(
        select(func.count(User.id))
        .where(User.tenant_id == tenant_id)
    )
    
    return {
        "tenant": {
            "id": tenant.id,
            "company_name": tenant.company_name,
            "tenant_type": tenant.tenant_type.value if hasattr(tenant.tenant_type, "value") else tenant.tenant_type,
            "is_active": tenant.is_active,
            "created_at": tenant.created_at.isoformat() if tenant.created_at else datetime.utcnow().isoformat()
        },
        "stats": {
            "workspaces": workspace_count.scalar(),
            "users": user_count.scalar()
        }
    }


@router.post("/tenants/{tenant_id}/toggle")
async def toggle_tenant_status(
    tenant_id: str,
    is_active: bool = Query(...),
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Activate or deactivate a tenant.
    """
    result = db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    
    tenant.is_active = is_active
    db.commit()
    
    logger.info(f"Admin {current.user_id} {'activated' if is_active else 'deactivated'} tenant {tenant_id}")
    
    return {
        "status": "success",
        "tenant_id": tenant_id,
        "is_active": is_active
    }


# ============================================================================
# AGENT MONITORING ENDPOINTS
# ============================================================================

@router.get("/agents/activity")
async def get_system_agent_activity(
    limit: int = Query(100, ge=1, le=500),
    agent_persona: Optional[str] = Query(None),
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get system-wide agent activity across all tenants.
    """
    query = select(AgentActionLog).order_by(AgentActionLog.created_at.desc()).limit(limit)
    
    if agent_persona:
        query = query.where(AgentActionLog.agent_persona == agent_persona)
    
    result = db.execute(query)
    logs = result.scalars().all()
    
    return {
        "total": len(logs),
        "logs": [
            {
                "id": log.id,
                "workspace_id": log.workspace_id,
                "agent_persona": log.agent_persona,
                "action_summary": log.action_summary,
                "status": log.status,
                "created_at": log.created_at.isoformat() if log.created_at else datetime.utcnow().isoformat()
            }
            for log in logs
        ]
    }


@router.get("/agents/stats")
async def get_agent_stats(
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get agent performance statistics.
    """
    # Count by agent
    agent_counts = db.execute(
        select(
            AgentActionLog.agent_persona,
            func.count(AgentActionLog.id)
        )
        .group_by(AgentActionLog.agent_persona)
    )
    
    # Count by status
    status_counts = db.execute(
        select(
            AgentActionLog.status,
            func.count(AgentActionLog.id)
        )
        .group_by(AgentActionLog.status)
    )
    
    return {
        "by_agent": {
            row.agent_persona: row.count
            for row in agent_counts.all()
        },
        "by_status": {
            row.status: row.count
            for row in status_counts.all()
        }
    }


# ============================================================================
# RATE LIMITING ENDPOINTS
# ============================================================================

@router.get("/rate-limits")
async def get_rate_limits(
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get current rate limit configuration and usage.
    """
    # In production, would fetch from Redis
    return {
        "status": "success",
        "global_limit": {
            "rpm": 6000,
            "current_usage": 847,
            "percentage": 14.1
        },
        "per_tenant_limit": {
            "rpm": 600,
            "tenants_near_limit": []
        }
    }


@router.post("/rate-limits/update")
async def update_rate_limits(
    global_rpm: int = Query(..., description="Global requests per minute limit"),
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update global rate limit.
    """
    if global_rpm < 100 or global_rpm > 100000:
        raise HTTPException(400, "Rate limit must be between 100 and 100000 RPM")
    
    # In production, would update Redis config
    logger.info(f"Admin {current.user_id} updated global rate limit to {global_rpm} RPM")
    
    return {
        "status": "success",
        "global_rpm": global_rpm
    }


# ============================================================================
# EMERGENCY CONTROLS ENDPOINTS
# ============================================================================

@router.post("/agents/override")
async def admin_override(
    action: str = Query(..., description="Action: pause_all, resume_all, force_compliance_check, reset_state"),
    reason: str = Query(...),
    target_workspace_id: Optional[str] = Query(None),
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Execute emergency admin override actions.
    """
    valid_actions = ["pause_all", "resume_all", "force_compliance_check", "reset_state"]
    
    if action not in valid_actions:
        raise HTTPException(400, f"Invalid action. Must be one of: {valid_actions}")
    
    # Log the override
    log = AgentActionLog(
        id=f"log_admin_{datetime.utcnow().timestamp()}",
        workspace_id=target_workspace_id or "system",
        agent_persona="Global_Admin",
        action_summary=f"Admin override: {action}",
        detailed_reasoning=reason,
        status="EXECUTED",
        created_at=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    logger.critical(f"ADMIN OVERRIDE by {current.user_id}: {action} - {reason}")
    
    return {
        "status": "executed",
        "action": action,
        "target": target_workspace_id or "system-wide",
        "reason": reason
    }


# ============================================================================
# API SPEND MONITORING ENDPOINTS
# ============================================================================

@router.get("/api-spend")
async def get_api_spend(
    period: str = Query("24h", description="Time period: 24h, 7d, 30d"),
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get API usage and spend across all services.
    """
    # In production, would aggregate from multiple sources
    return {
        "status": "success",
        "period": period,
        "services": {
            "qwen_ai": {
                "calls": 12847,
                "tokens": 25694000,
                "cost_usd": 1247.50
            },
            "meta_api": {
                "calls": 8420,
                "cost_usd": 0
            },
            "tiktok_api": {
                "calls": 3127,
                "cost_usd": 0
            },
            "stripe": {
                "calls": 1284,
                "cost_usd": 0
            }
        },
        "total_cost_usd": 1247.50
    }


# ============================================================================
# APPROVALS MONITORING ENDPOINTS
# ============================================================================

@router.get("/approvals")
async def get_system_approvals(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get system-wide approval queue.
    """
    query = select(ApprovalQueue)
    
    if status:
        try:
            status_enum = ApprovalStatus(status)
            query = query.where(ApprovalQueue.status == status_enum)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")
    
    query = query.order_by(ApprovalQueue.created_at.desc()).limit(limit)
    result = db.execute(query)
    approvals = result.scalars().all()
    
    return {
        "total": len(approvals),
        "approvals": [
            {
                "id": a.id,
                "workspace_id": a.workspace_id,
                "agent_persona": a.agent_persona,
                "action_type": a.action_type,
                "title": a.title,
                "status": a.status.value if hasattr(a.status, "value") else a.status,
                "created_at": a.created_at.isoformat() if a.created_at else datetime.utcnow().isoformat()
            }
            for a in approvals
        ]
    }


# ============================================================================
# USER MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/users")
async def list_users(
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    List users with optional tenant filter.
    """
    query = select(User)
    
    if tenant_id:
        query = query.where(User.tenant_id == tenant_id)
    
    query = query.order_by(User.created_at.desc()).limit(limit)
    result = db.execute(query)
    users = result.scalars().all()
    
    return {
        "total": len(users),
        "users": [
            {
                "id": u.id,
                "tenant_id": u.tenant_id,
                "email": u.email,
                "name": u.name,
                "is_global_admin": u.is_global_admin,
                "created_at": u.created_at.isoformat() if u.created_at else datetime.utcnow().isoformat()
            }
            for u in users
        ]
    }


# ============================================================================
# INTEGRATIONS MONITORING ENDPOINTS
# ============================================================================

@router.get("/integrations")
async def list_system_integrations(
    platform: Optional[str] = Query(None),
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    List all integrations across all tenants.
    """
    query = select(SecureIntegration)
    
    if platform:
        try:
            platform_enum = IntegrationPlatform(platform)
            query = query.where(SecureIntegration.platform == platform_enum)
        except ValueError:
            raise HTTPException(400, f"Invalid platform: {platform}")
    
    result = db.execute(query)
    integrations = result.scalars().all()
    
    return {
        "total": len(integrations),
        "integrations": [
            {
                "id": i.id,
                "workspace_id": i.workspace_id,
                "platform": i.platform.value if hasattr(i.platform, "value") else i.platform,
                "external_account_id": i.external_account_id,
                "is_valid": i.is_valid,
                "token_expires_at": i.token_expires_at.isoformat() if i.token_expires_at else None
            }
            for i in integrations
        ]
    }


# ============================================================================
# DYNAMIC SYSTEM CONFIG OVERRIDES
# ============================================================================

@router.get("/config/status")
async def get_simulator_config_status(
    current: CurrentUser = Depends(require_admin)
):
    """
    Get current simulator toggle and key presence status.
    """
    from app.agents.qwen_client import qwen_client
    from app.config import settings
    has_api_key = bool(qwen_client.api_key and "placeholder" not in qwen_client.api_key.lower() and qwen_client.api_key.strip())
    return {
        "force_simulator": getattr(qwen_client, "force_simulator", False),
        "has_api_key": has_api_key,
        "model": qwen_client.model,
        "api_base": settings.DASHSCOPE_BASE_URL
    }


@router.post("/config/toggle-simulator")
async def toggle_simulator_config(
    force_simulator: bool = Query(...),
    current: CurrentUser = Depends(require_admin)
):
    """
    Toggle the dynamic force simulator status system-wide.
    """
    from app.agents.qwen_client import qwen_client
    qwen_client.force_simulator = force_simulator
    return {
        "status": "success",
        "force_simulator": qwen_client.force_simulator,
        "message": f"LLM client simulator toggle set to {qwen_client.force_simulator}"
    }


# ============================================================================
# REAL-TIME DATABASE EXPLORER
# ============================================================================

@router.get("/database/explorer")
async def database_explorer(
    table_name: Optional[str] = Query(None),
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Explore database tables and row counts, or fetch rows for a specific table in real time.
    """
    from app.models import Campaign, CampaignMetric  # Inline import to prevent circular dependency
    
    tables_map = {
        "tenants": Tenant,
        "users": User,
        "client_workspaces": ClientWorkspace,
        "secure_integrations": SecureIntegration,
        "agent_action_logs": AgentActionLog,
        "approval_queue": ApprovalQueue,
        "campaigns": Campaign,
        "campaign_metrics": CampaignMetric,
    }
    
    # 1. Gather row counts for all supported tables
    counts = {}
    for name, model in tables_map.items():
        cnt_result = db.execute(select(func.count()).select_from(model))
        counts[name] = cnt_result.scalar()
        
    # 2. If a specific table is requested, fetch the rows
    rows_data = []
    columns = []
    if table_name and table_name in tables_map:
        model = tables_map[table_name]
        query = select(model).limit(50)
        
        # Order chronologically for logs/queues/metrics
        if hasattr(model, "created_at"):
            query = query.order_by(desc(model.created_at))
            
        result = db.execute(query)
        rows = result.scalars().all()
        
        columns = [col.name for col in model.__table__.columns]
        for r in rows:
            row_dict = {}
            for col in columns:
                val = getattr(r, col)
                if isinstance(val, datetime):
                    row_dict[col] = val.isoformat()
                elif hasattr(val, "value"):
                    row_dict[col] = val.value
                else:
                    row_dict[col] = val
            rows_data.append(row_dict)
            
    return {
        "tables": counts,
        "selected_table": table_name,
        "columns": columns,
        "rows": rows_data
    }


# ============================================================================
# GLOBAL OAUTH CONFIGURATION ENDPOINTS (Super Admin Panel)
# ============================================================================

from pydantic import BaseModel
class GlobalOauthConfigPayload(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: Optional[str] = None


@router.get("/config/oauth")
async def get_all_global_oauth_configs(
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Retrieve status and configurations of all global system developer app keys.
    Secrets are masked for security.
    """
    stmt = select(SystemIntegrationConfig)
    result = db.execute(stmt)
    configs = result.scalars().all()
    
    # Pre-populate empty entries for all platform platforms
    platforms = [p.value for p in IntegrationPlatform]
    config_map = {c.platform.value if hasattr(c.platform, "value") else c.platform: c for c in configs}
    
    status_list = []
    for p in platforms:
        config = config_map.get(p)
        status_list.append({
            "platform": p,
            "configured": config is not None,
            "client_id": config.client_id if config else "",
            "redirect_uri": config.redirect_uri if config else None,
            "updated_at": config.updated_at.isoformat() if config else None
        })
        
    return {
        "status": "success",
        "configs": status_list
    }


@router.post("/config/oauth/{platform}")
async def save_global_oauth_config(
    platform: str,
    payload: GlobalOauthConfigPayload,
    current: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Save or update system-wide global developer credentials for a platform.
    """
    try:
        platform_enum = IntegrationPlatform(platform.lower())
    except ValueError:
        raise HTTPException(400, f"Invalid platform name: {platform}")
        
    from app.auth.security import encrypt_token
    encrypted_secret = encrypt_token(payload.client_secret)
    
    # Check if config already exists
    stmt = select(SystemIntegrationConfig).where(SystemIntegrationConfig.platform == platform_enum)
    result = db.execute(stmt)
    config = result.scalar_one_or_none()
    
    if config:
        config.client_id = payload.client_id
        config.encrypted_client_secret = encrypted_secret
        config.redirect_uri = payload.redirect_uri
    else:
        config = SystemIntegrationConfig(
            platform=platform_enum,
            client_id=payload.client_id,
            encrypted_client_secret=encrypted_secret,
            redirect_uri=payload.redirect_uri
        )
        db.add(config)
        
    db.commit()
    return {
        "status": "success",
        "message": f"Global system developer credentials saved for {platform} successfully."
    }
