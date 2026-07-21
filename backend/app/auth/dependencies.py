import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import get_db
from app.models import User, ClientWorkspace
from app.auth.security import decode_access_token

security = HTTPBearer()

class CurrentUser:
    def __init__(self, user_id: str, tenant_id: str, role: str, is_global_admin: bool):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role
        self.is_global_admin = is_global_admin

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),  # CHANGED TO SYNC SESSION
) -> CurrentUser:
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    result = db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(401, "User not found")
    
    return CurrentUser(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=payload.get("role", "client"),
        is_global_admin=user.is_global_admin,
    )


async def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not current_user.is_global_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def verify_workspace_access(
    workspace_id: str,
    current_user: CurrentUser,
    db: Session,
) -> ClientWorkspace:
    result = db.execute(select(ClientWorkspace).where(ClientWorkspace.id == workspace_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not current_user.is_global_admin and workspace.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied to this workspace")
    return workspace
