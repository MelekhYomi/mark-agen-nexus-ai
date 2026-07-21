import uuid
import re
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Tenant, TenantType, ClientWorkspace
from app.auth.security import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user, CurrentUser
from app.agents.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)
    name: str = Field(..., min_length=2, max_length=100)
    company_name: str = Field(..., min_length=2, max_length=255)
    tenant_type: str = "saas_subscriber"
    brand_name: Optional[str] = None
    autopilot_enabled: bool = False
    monthly_budget_cap: int = 5000
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Password must contain:
        - At least 12 characters
        - Uppercase letter
        - Lowercase letter
        - Digit
        - Special character (!@#$%^&*)
        """
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain digit')
        if not re.search(r'[!@#$%^&*]', v):
            raise ValueError('Password must contain special character (!@#$%^&*)')
        return v
    
    @field_validator('company_name')
    @classmethod
    def sanitize_company_name(cls, v: str) -> str:
        """Remove leading/trailing whitespace"""
        return v.strip()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    try:
        # Check if email already exists
        existing = db.execute(select(User).where(User.email == req.email))
        if existing.scalar_one_or_none():
            raise HTTPException(409, "Email already registered")
        
        # Check if tenant company name already exists
        existing_tenant = db.execute(select(Tenant).where(Tenant.company_name == req.company_name))
        if existing_tenant.scalar_one_or_none():
            raise HTTPException(409, "Company name already registered")

        # Create tenant
        tenant_id = f"t_{uuid.uuid4().hex[:14]}"
        tenant = Tenant(
            id=tenant_id,
            company_name=req.company_name,
            tenant_type=TenantType(req.tenant_type),
            is_active=True,
        )
        db.add(tenant)
        db.flush()
        
        # Create user
        user_id = f"u_{uuid.uuid4().hex[:14]}"
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            email=req.email,
            hashed_password=hash_password(req.password),
            name=req.name,
            is_active=True,
        )
        db.add(user)
        db.flush()

        # Create client workspace
        ws_id = f"w_{uuid.uuid4().hex[:14]}"
        brand = req.brand_name or req.company_name
        workspace = ClientWorkspace(
            id=ws_id,
            tenant_id=tenant_id,
            brand_name=brand,
            brand_voice_profile="Autonomous, performance-oriented",
            autopilot_enabled=req.autopilot_enabled,
            monthly_budget_cap=req.monthly_budget_cap,
            is_active=True
        )
        db.add(workspace)
        db.commit()

        # Run a real agent cycle immediately so the new workspace's dashboard
        # shows genuine agent-generated activity (real agent names, real
        # Qwen-produced content/reasoning) instead of scripted placeholder text.
        # A failure here must not block account creation.
        try:
            orchestrator = AgentOrchestrator(db, ws_id)
            orchestrator.run_full_cycle()
        except Exception as agent_error:
            logger.error(f"Initial agent cycle failed for new workspace {ws_id}: {agent_error}")

        token = create_access_token(user_id, tenant_id, "client")
        return {
            "access_token": token,
            "user": {
                "id": user_id,
                "email": req.email,
                "name": req.name,
                "workspace_id": ws_id
            }
        }
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(500, f"Registration failed: {str(e)}")

@router.post("/login")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    result = db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    
    tenant_result = db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_result.scalar_one()
    if not tenant.is_active:
        raise HTTPException(403, "Account deactivated")
    
    token = create_access_token(user.id, user.tenant_id, "client", user.is_global_admin)
    return {
        "access_token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "company": tenant.company_name,
            "is_global_admin": user.is_global_admin,
            "billing_plan": tenant.billing_plan,
        }
    }

@router.get("/me")
async def get_me(current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    result = db.execute(select(User).where(User.id == current.user_id))
    user = result.scalar_one()
    tenant_result = db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_result.scalar_one()
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_global_admin": user.is_global_admin,
            "billing_plan": tenant.billing_plan,
        },
        "tenant": {
            "id": tenant.id,
            "company_name": tenant.company_name,
            "billing_plan": tenant.billing_plan,
        }
    }


@router.get("/plan-capabilities")
async def get_plan_capabilities(db: Session = Depends(get_db)):
    """
    Get all active subscription plan capabilities (Starter, Professional, Agency).
    """
    from app.models import PlanConfig
    result = db.execute(select(PlanConfig))
    plans = result.scalars().all()
    return {
        "status": "success",
        "plans": {
            p.id: {
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
        }
    }