"""
Dashboard Router
Provides endpoints for workspace management, agent activity, approvals, and overview data.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    ClientWorkspace, AgentActionLog, ApprovalQueue, ApprovalStatus,
    Tenant, User, SecureIntegration, IntegrationPlatform
)
from app.auth.dependencies import get_current_user, CurrentUser, verify_workspace_access
from app.agents.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ============================================================================
# WORKSPACE ENDPOINTS
# ============================================================================

@router.get("/workspaces")
async def list_workspaces(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all workspaces for the current user's tenant.
    Returns workspace list with basic info.
    """
    result = db.execute(
        select(ClientWorkspace)
        .where(ClientWorkspace.tenant_id == current.tenant_id)
        .order_by(ClientWorkspace.created_at.desc())
    )
    workspaces = result.scalars().all()
    
    return {
        "workspaces": [
            {
                "id": w.id,
                "brand_name": w.brand_name,
                "autopilot_enabled": w.autopilot_enabled,
                "monthly_budget_cap": w.monthly_budget_cap,
                "roas_threshold": w.roas_threshold,
                "brand_voice_profile": w.brand_voice_profile,
                "created_at": w.created_at.isoformat()
            }
            for w in workspaces
        ],
        "total": len(workspaces)
    }


@router.get("/summary")
async def get_workspace_summary(
    workspace_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get workspace summary including agent activity counts and pending approvals.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    # Count agent logs
    logs_count = db.execute(
        select(func.count(AgentActionLog.id))
        .where(AgentActionLog.workspace_id == workspace_id)
    )
    
    # Count pending approvals
    approvals_count = db.execute(
        select(func.count(ApprovalQueue.id))
        .where(
            ApprovalQueue.workspace_id == workspace_id,
            ApprovalQueue.status == ApprovalStatus.PENDING
        )
    )
    
    # Get recent logs
    recent_logs = db.execute(
        select(AgentActionLog)
        .where(AgentActionLog.workspace_id == workspace_id)
        .order_by(AgentActionLog.created_at.desc())
        .limit(10)
    )
    
    # Count by agent
    agent_counts = db.execute(
        select(
            AgentActionLog.agent_persona,
            func.count(AgentActionLog.id)
        )
        .where(AgentActionLog.workspace_id == workspace_id)
        .group_by(AgentActionLog.agent_persona)
    )
    
    return {
        "workspace_id": workspace_id,
        "total_logs": logs_count.scalar(),
        "pending_approvals": approvals_count.scalar(),
        "recent_actions": [
            {
                "id": log.id,
                "agent": log.agent_persona,
                "summary": log.action_summary,
                "status": log.status,
                "timestamp": log.created_at.isoformat()
            }
            for log in recent_logs.scalars().all()
        ],
        "agent_breakdown": {
            row.agent_persona: row.count
            for row in agent_counts.all()
        }
    }


# ============================================================================
# AGENT LOGS ENDPOINTS
# ============================================================================

@router.get("/agent-logs")
async def get_agent_logs(
    workspace_id: str,
    agent_persona: Optional[str] = Query(None, description="Filter by agent name"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get agent action logs with filtering and pagination.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    query = select(AgentActionLog).where(
        AgentActionLog.workspace_id == workspace_id
    )
    
    if agent_persona:
        query = query.where(AgentActionLog.agent_persona == agent_persona)
    
    if status:
        query = query.where(AgentActionLog.status == status)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (db.execute(count_query)).scalar()
    
    # Get paginated results
    query = query.order_by(AgentActionLog.created_at.desc()).offset(offset).limit(limit)
    result = db.execute(query)
    logs = result.scalars().all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": [
            {
                "id": log.id,
                "agent_persona": log.agent_persona,
                "action_summary": log.action_summary,
                "detailed_reasoning": log.detailed_reasoning,
                "status": log.status,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]
    }


# ============================================================================
# APPROVALS ENDPOINTS
# ============================================================================

@router.get("/approvals")
async def get_approvals(
    workspace_id: str,
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get approval queue with filtering and pagination.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    query = select(ApprovalQueue).where(
        ApprovalQueue.workspace_id == workspace_id
    )
    
    if status_filter:
        try:
            status_enum = ApprovalStatus(status_filter.lower())
            query = query.where(ApprovalQueue.status == status_enum)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status_filter}")
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (db.execute(count_query)).scalar()
    
    # Get paginated results
    query = query.order_by(ApprovalQueue.created_at.desc()).offset(offset).limit(limit)
    result = db.execute(query)
    approvals = result.scalars().all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "approvals": [
            {
                "id": a.id,
                "agent_persona": a.agent_persona,
                "action_type": a.action_type,
                "title": a.title,
                "description": a.description,
                "payload": a.payload,
                "risk_score": a.risk_score,
                "status": a.status.value,
                "reviewed_by": a.reviewed_by,
                "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
                "created_at": a.created_at.isoformat()
            }
            for a in approvals
        ]
    }


@router.post("/approvals/{approval_id}/review")
async def review_approval(
    approval_id: str,
    decision: str = Query(..., description="approved or rejected"),
    notes: Optional[str] = Query(None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve or reject a pending action.
    """
    result = db.execute(
        select(ApprovalQueue).where(ApprovalQueue.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    
    if not approval:
        raise HTTPException(404, "Approval not found")
    
    # Verify workspace access
    await verify_workspace_access(approval.workspace_id, current, db)
    
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(400, f"Approval already {approval.status.value}")
    
    # Update approval status
    if decision == "approved":
        approval.status = ApprovalStatus.APPROVED
        
        # Execute the approved action
        try:
            orchestrator = AgentOrchestrator(db, approval.workspace_id)
            # Execute based on action type
            if approval.action_type == "publish_post":
                # Would call social manager to publish
                orchestrator._log_action(
                    approval.agent_persona,
                    f"Executed approved action: {approval.title}",
                    "EXECUTED"
                )
            elif approval.action_type == "adjust_budget":
                # Would call ads manager to adjust budget
                orchestrator._log_action(
                    approval.agent_persona,
                    f"Executed budget adjustment: {approval.title}",
                    "EXECUTED"
                )
        except Exception as e:
            logger.error(f"Failed to execute approval: {e}")
            approval.status = ApprovalStatus.FAILED
        
    elif decision == "rejected":
        approval.status = ApprovalStatus.REJECTED
    else:
        raise HTTPException(400, "Invalid decision. Use 'approved' or 'rejected'")
    
    approval.reviewed_by = current.user_id
    approval.reviewed_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "status": "success",
        "approval_id": approval_id,
        "decision": approval.status.value
    }


# ============================================================================
# OPTIMIZATION ENDPOINTS
# ============================================================================

@router.post("/agents/optimize")
async def trigger_optimization(
    workspace_id: str,
    roas_threshold: float = Query(2.0, description="ROAS threshold for optimization"),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger a full agent optimization cycle.
    Runs all 5 agents in sequence to analyze and optimize performance.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    orchestrator = AgentOrchestrator(db, workspace_id)
    result = orchestrator.run_full_cycle()
    
    return {
        "status": "completed",
        "workspace_id": workspace_id,
        "timestamp": result["timestamp"],
        "summary": result.get("summary", {}),
        "agents": {
            agent: {
                "status": "success" if "error" not in data else "error",
                "tokens_used": data.get("tokens_used", 0)
            }
            for agent, data in result.get("agents", {}).items()
        }
    }


@router.post("/agents/society-demo")
async def run_agent_society_demo(
    workspace_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Run the full 13-agent society cycle and return it alongside the actual
    AgentActionLog entries it produced, as auditable proof of multi-agent
    collaboration (task division + conflict resolution, e.g. Brand Guardian
    reviewing and potentially blocking Social Manager's content before publish).
    """
    await verify_workspace_access(workspace_id, current, db)

    orchestrator = AgentOrchestrator(db, workspace_id)
    result = orchestrator.run_full_cycle()

    logs_query = (
        select(AgentActionLog)
        .where(AgentActionLog.workspace_id == workspace_id)
        .order_by(desc(AgentActionLog.created_at))
        .limit(30)
    )
    logs = db.execute(logs_query).scalars().all()

    approvals_query = (
        select(ApprovalQueue)
        .where(ApprovalQueue.workspace_id == workspace_id)
        .order_by(desc(ApprovalQueue.created_at))
        .limit(10)
    )
    approvals = db.execute(approvals_query).scalars().all()

    return {
        "status": "completed",
        "workspace_id": workspace_id,
        "timestamp": result["timestamp"],
        "cycle_summary": result.get("summary", {}),
        "agent_collaboration_proof": [
            {
                "agent": log.agent_persona,
                "action": log.action_summary,
                "reasoning": log.detailed_reasoning,
                "status": log.status,
                "timestamp": log.created_at.isoformat()
            }
            for log in logs
        ],
        "pending_human_review": [
            {
                "flagged_by": a.agent_persona,
                "action_type": a.action_type,
                "title": a.title,
                "description": a.description,
                "risk_score": a.risk_score,
                "status": a.status.value,
                "timestamp": a.created_at.isoformat()
            }
            for a in approvals
        ]
    }


@router.post("/agents/{agent_name}/run")
async def run_single_agent(
    agent_name: str,
    workspace_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    kwargs: Dict[str, Any] = {}
):
    """
    Run a specific agent individually.
    Agent names: social_manager, digital_marketer, ads_manager, seo_expert, analytics
    """
    await verify_workspace_access(workspace_id, current, db)
    
    orchestrator = AgentOrchestrator(db, workspace_id)
    result = orchestrator.run_single_agent(agent_name, **kwargs)
    
    return {
        "status": "completed",
        "agent": agent_name,
        "result": result
    }


# ============================================================================
# INTEGRATIONS ENDPOINTS
# ============================================================================

@router.get("/integrations")
async def list_integrations(
    workspace_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all connected integrations for a workspace.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    result = db.execute(
        select(SecureIntegration)
        .where(SecureIntegration.workspace_id == workspace_id)
        .order_by(SecureIntegration.created_at.desc())
    )
    integrations = result.scalars().all()
    
    return {
        "integrations": [
            {
                "id": i.id,
                "platform": i.platform.value,
                "external_account_id": i.external_account_id,
                "external_account_name": i.external_account_name,
                "is_valid": i.is_valid,
                "token_expires_at": i.token_expires_at.isoformat() if i.token_expires_at else None,
                "created_at": i.created_at.isoformat()
            }
            for i in integrations
        ],
        "total": len(integrations)
    }


@router.delete("/integrations/{platform}")
async def disconnect_integration(
    platform: str,
    workspace_id: str = Query(...),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect/Delete an integration for a workspace.
    """
    await verify_workspace_access(workspace_id, current, db)
    try:
        platform_enum = IntegrationPlatform(platform.lower())
    except ValueError:
        raise HTTPException(400, f"Invalid platform: {platform}")
        
    stmt = select(SecureIntegration).where(
        SecureIntegration.workspace_id == workspace_id,
        SecureIntegration.platform == platform_enum
    )
    result = db.execute(stmt)
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(404, f"No active integration found for {platform}")
        
    db.delete(integration)
    db.commit()
    
    # Log the action
    orchestrator = AgentOrchestrator(db, workspace_id)
    orchestrator._log_action(
        "System",
        f"Disconnected {platform.capitalize()} integration",
        "EXECUTED"
    )
    
    return {"status": "success", "message": f"Successfully disconnected {platform} integration."}


# ============================================================================
# WORKSPACE SETTINGS ENDPOINTS
# ============================================================================

@router.post("/workspaces/{workspace_id}/toggle-autopilot")
async def toggle_autopilot(
    workspace_id: str,
    enabled: bool = Query(...),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Toggle autopilot mode for a workspace.
    When enabled, agents can execute low-risk actions without approval.
    """
    workspace = await verify_workspace_access(workspace_id, current, db)
    
    workspace.autopilot_enabled = enabled
    db.commit()
    
    # Log the change
    orchestrator = AgentOrchestrator(db, workspace_id)
    orchestrator._log_action(
        "System",
        f"Autopilot mode {'enabled' if enabled else 'disabled'}",
        "EXECUTED"
    )
    
    return {
        "workspace_id": workspace_id,
        "autopilot_enabled": enabled,
        "mode": "AUTOPILOT" if enabled else "CO-PILOT"
    }


@router.put("/workspaces/{workspace_id}/settings")
async def update_workspace_settings(
    workspace_id: str,
    monthly_budget_cap: int = Query(..., description="Monthly budget cap in cents"),
    roas_threshold: float = Query(2.0, description="Minimum ROAS threshold"),
    brand_voice_profile: Optional[str] = Query(None, description="Brand voice profile description"),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update workspace configuration settings (budget, ROAS, brand voice).
    """
    workspace = await verify_workspace_access(workspace_id, current, db)
    
    if monthly_budget_cap < 0:
        raise HTTPException(400, "Budget cap cannot be negative")
    if roas_threshold < 0:
        raise HTTPException(400, "ROAS threshold cannot be negative")
        
    workspace.monthly_budget_cap = monthly_budget_cap
    workspace.roas_threshold = roas_threshold
    if brand_voice_profile is not None:
        workspace.brand_voice_profile = brand_voice_profile
        
    db.commit()
    
    return {
        "workspace_id": workspace_id,
        "monthly_budget_cap": workspace.monthly_budget_cap,
        "roas_threshold": workspace.roas_threshold,
        "brand_voice_profile": workspace.brand_voice_profile
    }


@router.put("/workspaces/{workspace_id}/budget")
async def update_budget_cap(
    workspace_id: str,
    monthly_budget_cap: int = Query(..., description="Monthly budget cap in cents"),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update monthly budget cap for a workspace.
    """
    workspace = await verify_workspace_access(workspace_id, current, db)
    
    if monthly_budget_cap < 0:
        raise HTTPException(400, "Budget cap cannot be negative")
    
    workspace.monthly_budget_cap = monthly_budget_cap
    db.commit()
    
    return {
        "workspace_id": workspace_id,
        "monthly_budget_cap": monthly_budget_cap,
        "monthly_budget_cap_formatted": f"${monthly_budget_cap / 100:.2f}"
    }