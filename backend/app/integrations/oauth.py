"""
OAuth Integration Router
Handles OAuth 2.0 flows for all social media platforms.
Implements secure state management, token exchange, and credential storage.
"""
import os
import json
import hashlib
import base64
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs

import httpx
from fastapi import APIRouter, HTTPException, Request, Depends, Query, Header
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.config import settings
from app.database import get_db
from app.models import SecureIntegration, IntegrationPlatform, WorkspaceIntegrationConfig, SystemIntegrationConfig
from app.auth.security import encrypt_token, decrypt_token
from app.auth.dependencies import get_current_user, CurrentUser

router = APIRouter(tags=["OAuth"])


class PlatformConfigPayload(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: Optional[str] = None


async def get_oauth_user(
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> CurrentUser:
    token_str = None
    if token:
        token_str = token
    elif authorization and authorization.startswith("Bearer "):
        token_str = authorization.split(" ")[1]
        
    if not token_str:
        raise HTTPException(status_code=401, detail="Authentication credentials missing")
        
    try:
        from app.auth.security import decode_access_token
        payload = decode_access_token(token_str)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
        
    from app.models import User
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


def get_default_redirect_uri(platform: str) -> str:
    """Helper to return default redirect URI for callback"""
    return f"{settings.BACKEND_URL}/api/v1/auth/callback/{platform.lower()}"


def resolve_credentials(
    workspace_id: str,
    platform: str,
    db: Session
) -> tuple[str, str, str]:
    """
    Resolve client_id, client_secret, and redirect_uri for a platform.
    First checks workspace-specific WorkspaceIntegrationConfig.
    Falls back to settings system environment variables.
    """
    platform_enum = IntegrationPlatform(platform.lower())
    
    # Check custom workspace config
    stmt = select(WorkspaceIntegrationConfig).where(
        WorkspaceIntegrationConfig.workspace_id == workspace_id,
        WorkspaceIntegrationConfig.platform == platform_enum
    )
    result = db.execute(stmt)
    config = result.scalar_one_or_none()
    
    if config:
        client_secret = decrypt_token(config.encrypted_client_secret)
        # Use workspace redirect_uri or default system redirect_uri
        redirect_uri = config.redirect_uri or get_default_redirect_uri(platform)
        return config.client_id, client_secret, redirect_uri
        
    # Check global admin DB config (Super Admin Dashboard settings)
    stmt_global = select(SystemIntegrationConfig).where(
        SystemIntegrationConfig.platform == platform_enum
    )
    result_global = db.execute(stmt_global)
    global_config = result_global.scalar_one_or_none()
    
    if global_config:
        client_secret = decrypt_token(global_config.encrypted_client_secret)
        # Use global redirect_uri or default system redirect_uri
        redirect_uri = global_config.redirect_uri or get_default_redirect_uri(platform)
        return global_config.client_id, client_secret, redirect_uri
        
    # Fallback to static system environment settings (.env)
    if platform == "meta":
        return settings.META_APP_ID, settings.META_APP_SECRET, settings.META_REDIRECT_URI
    elif platform == "tiktok":
        return settings.TIKTOK_APP_ID, settings.TIKTOK_APP_SECRET, settings.TIKTOK_REDIRECT_URI
    elif platform == "twitter":
        return settings.TWITTER_CLIENT_ID, settings.TWITTER_CLIENT_SECRET, settings.TWITTER_REDIRECT_URI
    elif platform == "linkedin":
        return settings.LINKEDIN_CLIENT_ID, settings.LINKEDIN_CLIENT_SECRET, settings.LINKEDIN_REDIRECT_URI
    elif platform == "google":
        return settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET, settings.GOOGLE_REDIRECT_URI
    elif platform == "pinterest":
        return settings.PINTEREST_CLIENT_ID, settings.PINTEREST_CLIENT_SECRET, settings.PINTEREST_REDIRECT_URI
        
    raise HTTPException(400, f"Unsupported or unconfigured OAuth platform: {platform}")


@router.post("/config/{platform}")
async def save_platform_config(
    platform: str,
    workspace_id: str,
    payload: PlatformConfigPayload,
    current_user: CurrentUser = Depends(get_oauth_user),
    db: Session = Depends(get_db)
):
    """
    Save custom developer keys for a platform within a workspace.
    Encrypts the client_secret securely before database storage.
    """
    from app.auth.dependencies import verify_workspace_access
    await verify_workspace_access(workspace_id, current_user, db)
    
    try:
        platform_enum = IntegrationPlatform(platform.lower())
    except ValueError:
        raise HTTPException(400, f"Invalid platform name: {platform}")
        
    # Check if a config already exists
    stmt = select(WorkspaceIntegrationConfig).where(
        WorkspaceIntegrationConfig.workspace_id == workspace_id,
        WorkspaceIntegrationConfig.platform == platform_enum
    )
    result = db.execute(stmt)
    existing_config = result.scalar_one_or_none()
    
    if payload.client_secret in ("••••••••••••••••", "••••••••••••"):
        if existing_config:
            encrypted_secret = existing_config.encrypted_client_secret
        else:
            raise HTTPException(400, "Client secret is required for new configurations.")
    else:
        encrypted_secret = encrypt_token(payload.client_secret)
        
    if existing_config:
        existing_config.client_id = payload.client_id
        existing_config.encrypted_client_secret = encrypted_secret
        existing_config.redirect_uri = payload.redirect_uri
        existing_config.updated_at = datetime.utcnow()
    else:
        new_config = WorkspaceIntegrationConfig(
            workspace_id=workspace_id,
            platform=platform_enum,
            client_id=payload.client_id,
            encrypted_client_secret=encrypted_secret,
            redirect_uri=payload.redirect_uri,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(new_config)
        
    db.commit()
    return {"status": "success", "message": f"Custom developer credentials saved for {platform}"}


@router.get("/config/{platform}")
async def get_platform_config(
    platform: str,
    workspace_id: str,
    current_user: CurrentUser = Depends(get_oauth_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve saved custom developer configuration.
    Masks the Client Secret for security reasons.
    """
    from app.auth.dependencies import verify_workspace_access
    await verify_workspace_access(workspace_id, current_user, db)
    
    try:
        platform_enum = IntegrationPlatform(platform.lower())
    except ValueError:
        raise HTTPException(400, f"Invalid platform name: {platform}")
        
    stmt = select(WorkspaceIntegrationConfig).where(
        WorkspaceIntegrationConfig.workspace_id == workspace_id,
        WorkspaceIntegrationConfig.platform == platform_enum
    )
    result = db.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        return {"configured": False, "client_id": "", "redirect_uri": get_default_redirect_uri(platform)}
        
    return {
        "configured": True,
        "client_id": config.client_id,
        "client_secret_masked": "••••••••••••••••",
        "redirect_uri": config.redirect_uri or get_default_redirect_uri(platform)
    }



def create_oauth_state(workspace_id: str, platform: str, user_id: str) -> str:
    """
    Create cryptographically secure OAuth state parameter.
    Prevents CSRF attacks and tracks the original request.
    """
    state_data = {
        "workspace_id": workspace_id,
        "platform": platform,
        "user_id": user_id,
        "timestamp": datetime.utcnow().timestamp(),
        "nonce": os.urandom(32).hex()
    }
    
    state_json = json.dumps(state_data)
    state_b64 = base64.urlsafe_b64encode(state_json.encode()).decode()
    
    # Create HMAC signature
    signature = hashlib.sha256(
        f"{state_b64}:{settings.OAUTH_STATE_SECRET}".encode()
    ).hexdigest()
    
    return f"{state_b64}.{signature}"


def verify_oauth_state(state: str) -> dict:
    """Verify and decode OAuth state parameter"""
    try:
        state_b64, signature = state.rsplit('.', 1)
        
        # Verify signature
        expected_signature = hashlib.sha256(
            f"{state_b64}:{settings.OAUTH_STATE_SECRET}".encode()
        ).hexdigest()
        
        if signature != expected_signature:
            raise ValueError("Invalid state signature")
        
        # Decode state
        state_json = base64.urlsafe_b64decode(state_b64.encode()).decode()
        oauth_state = json.loads(state_json)
        
        # Check expiration (15 minutes)
        if datetime.utcnow().timestamp() - oauth_state["timestamp"] > 900:
            raise ValueError("OAuth state expired")
        
        return oauth_state
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid OAuth state: {str(e)}"
        )


# ============================================================================
# META (FACEBOOK/INSTAGRAM) OAUTH
# ============================================================================

@router.get("/meta/authorize")
async def meta_authorize(
    workspace_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_oauth_user),
    db: Session = Depends(get_db)
):
    """
    Initiate Meta OAuth flow.
    Redirects user to Facebook authorization dialog.
    """
    # Verify workspace access
    from app.models import ClientWorkspace
    result = db.execute(
        select(ClientWorkspace).where(
            ClientWorkspace.id == workspace_id,
            ClientWorkspace.tenant_id == current_user.tenant_id
        )
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(404, "Workspace not found or access denied")
    
    # Create secure state
    state = create_oauth_state(workspace_id, "meta", current_user.user_id)
    
    # Resolve custom or default client credentials
    client_id, _, redirect_uri = resolve_credentials(workspace_id, "meta", db)
    
    # Meta OAuth parameters
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": ",".join([
            "ads_management",
            "ads_read",
            "business_management",
            "pages_manage_posts",
            "pages_read_engagement",
            "pages_show_list",
            "instagram_basic",
            "instagram_content_publish",
            "public_profile"
        ]),
        "state": state,
        "response_type": "code",
        "auth_type": "rerequest"
    }
    
    auth_url = f"https://www.facebook.com/v18.0/dialog/oauth?{urlencode(params)}"
    
    return RedirectResponse(url=auth_url)


@router.get("/callback/meta")
async def meta_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    error_description: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Handle Meta OAuth callback.
    Exchanges authorization code for long-lived access token.
    """
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"Meta authorization failed: {error} - {error_description}"
        )
    
    if not code or not state:
        raise HTTPException(400, "Missing authorization code or state")
    
    # Verify state
    oauth_state = verify_oauth_state(state)
    
    # Resolve custom or default credentials
    client_id, client_secret, redirect_uri = resolve_credentials(oauth_state["workspace_id"], "meta", db)
    
    try:
        # Step 1: Exchange code for short-lived token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "code": code
                }
            )
            token_response.raise_for_status()
            short_token_data = token_response.json()
        
        # Step 2: Exchange for long-lived token (60 days)
        async with httpx.AsyncClient() as client:
            long_token_response = await client.get(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "fb_exchange_token": short_token_data["access_token"]
                }
            )
            long_token_response.raise_for_status()
            long_token_data = long_token_response.json()
        
        # Step 3: Get user's pages and ad accounts
        async with httpx.AsyncClient() as client:
            pages_response = await client.get(
                "https://graph.facebook.com/v18.0/me/accounts",
                params={"access_token": long_token_data["access_token"]}
            )
            pages_response.raise_for_status()
            pages_data = pages_response.json()
        
        # Step 4: Store integration
        encrypted_token = encrypt_token(long_token_data["access_token"])
        
        integration = SecureIntegration(
            id=f"int_meta_{oauth_state['workspace_id']}",
            workspace_id=oauth_state["workspace_id"],
            platform=IntegrationPlatform.META,
            encrypted_access_token=encrypted_token,
            token_expires_at=datetime.utcnow() + timedelta(seconds=long_token_data.get("expires_in", 5184000)),
            external_account_id=pages_data["data"][0]["id"] if pages_data.get("data") else "pending",
            external_account_name=pages_data["data"][0]["name"] if pages_data.get("data") else "Meta Account",
            is_valid=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Upsert (update if exists, insert if not)
        existing = db.execute(
            select(SecureIntegration).where(SecureIntegration.id == integration.id)
        )
        if existing.scalar_one_or_none():
            db.merge(integration)
        else:
            db.add(integration)
        
        db.commit()
        
        # Redirect to success page
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/oauth/success?platform=meta&workspace_id={oauth_state['workspace_id']}"
        )
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Meta API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Integration failed: {str(e)}"
        )


# ============================================================================
# TIKTOK OAUTH
# ============================================================================

@router.get("/tiktok/authorize")
async def tiktok_authorize(
    workspace_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_oauth_user),
    db: Session = Depends(get_db)
):
    """Initiate TikTok OAuth flow"""
    from app.models import ClientWorkspace
    result = db.execute(
        select(ClientWorkspace).where(
            ClientWorkspace.id == workspace_id,
            ClientWorkspace.tenant_id == current_user.tenant_id
        )
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(404, "Workspace not found or access denied")
    
    state = create_oauth_state(workspace_id, "tiktok", current_user.user_id)
    client_id, _, redirect_uri = resolve_credentials(workspace_id, "tiktok", db)
    
    params = {
        "client_key": client_id,
        "redirect_uri": redirect_uri,
        "scope": ",".join([
            "user.info.basic",
            "video.upload",
            "video.list"
        ]),
        "state": state,
        "response_type": "code"
    }
    
    auth_url = f"https://www.tiktok.com/auth/authorize/?{urlencode(params)}"
    
    return RedirectResponse(url=auth_url)


@router.get("/callback/tiktok")
async def tiktok_callback(
    code: str = Query(None),
    state: str = Query(None),
    error_code: str = Query(None),
    error_message: str = Query(None),
    db: Session = Depends(get_db)
):
    """Handle TikTok OAuth callback"""
    if error_code:
        raise HTTPException(
            status_code=400,
            detail=f"TikTok authorization failed: {error_code} - {error_message}"
        )
    
    if not code or not state:
        raise HTTPException(400, "Missing authorization code or state")
    
    oauth_state = verify_oauth_state(state)
    client_id, client_secret, redirect_uri = resolve_credentials(oauth_state["workspace_id"], "tiktok", db)
    
    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://open.tiktokapis.com/v2/oauth/token/",
                json={
                    "client_key": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri
                }
            )
            token_response.raise_for_status()
            token_data = token_response.json()
        
        # Store integration
        encrypted_token = encrypt_token(token_data["data"]["access_token"])
        
        integration = SecureIntegration(
            id=f"int_tiktok_{oauth_state['workspace_id']}",
            workspace_id=oauth_state["workspace_id"],
            platform=IntegrationPlatform.TIKTOK,
            encrypted_access_token=encrypted_token,
            encrypted_refresh_token=encrypt_token(token_data["data"].get("refresh_token", "")),
            token_expires_at=datetime.utcnow() + timedelta(seconds=token_data["data"].get("expires_in", 86400)),
            external_account_id="pending",
            external_account_name="TikTok Account",
            is_valid=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        existing = db.execute(
            select(SecureIntegration).where(SecureIntegration.id == integration.id)
        )
        if existing.scalar_one_or_none():
            db.merge(integration)
        else:
            db.add(integration)
        
        db.commit()
        
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/oauth/success?platform=tiktok&workspace_id={oauth_state['workspace_id']}"
        )
        
    except Exception as e:
        raise HTTPException(500, f"Integration failed: {str(e)}")


# ============================================================================
# TWITTER/X OAUTH
# ============================================================================

@router.get("/twitter/authorize")
async def twitter_authorize(
    workspace_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_oauth_user),
    db: Session = Depends(get_db)
):
    """Initiate Twitter OAuth 2.0 flow"""
    from app.models import ClientWorkspace
    result = db.execute(
        select(ClientWorkspace).where(
            ClientWorkspace.id == workspace_id,
            ClientWorkspace.tenant_id == current_user.tenant_id
        )
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(404, "Workspace not found or access denied")
    
    state = create_oauth_state(workspace_id, "twitter", current_user.user_id)
    client_id, _, redirect_uri = resolve_credentials(workspace_id, "twitter", db)
    
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "tweet.read tweet.write users.read offline.access",
        "state": state,
        "code_challenge": "challenge",  # PKCE would be implemented here
        "code_challenge_method": "plain"
    }
    
    auth_url = f"https://twitter.com/i/oauth2/authorize?{urlencode(params)}"
    
    return RedirectResponse(url=auth_url)


@router.get("/callback/twitter")
async def twitter_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db)
):
    """Handle Twitter OAuth callback"""
    if error:
        raise HTTPException(400, f"Twitter authorization failed: {error}")
    
    if not code or not state:
        raise HTTPException(400, "Missing authorization code or state")
    
    oauth_state = verify_oauth_state(state)
    client_id, client_secret, redirect_uri = resolve_credentials(oauth_state["workspace_id"], "twitter", db)
    
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://api.twitter.com/2/oauth2/token",
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "client_id": client_id,
                    "redirect_uri": redirect_uri,
                    "code_verifier": "challenge"  # PKCE verifier matching plain challenge
                },
                auth=(client_id, client_secret)
            )
            token_response.raise_for_status()
            token_data = token_response.json()
        
        encrypted_token = encrypt_token(token_data["access_token"])
        
        integration = SecureIntegration(
            id=f"int_twitter_{oauth_state['workspace_id']}",
            workspace_id=oauth_state["workspace_id"],
            platform=IntegrationPlatform.TWITTER,
            encrypted_access_token=encrypted_token,
            encrypted_refresh_token=encrypt_token(token_data.get("refresh_token", "")),
            token_expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 7200)),
            external_account_id="pending",
            external_account_name="Twitter Account",
            is_valid=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        existing = db.execute(
            select(SecureIntegration).where(SecureIntegration.id == integration.id)
        )
        if existing.scalar_one_or_none():
            db.merge(integration)
        else:
            db.add(integration)
        
        db.commit()
        
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/oauth/success?platform=twitter&workspace_id={oauth_state['workspace_id']}"
        )
        
    except Exception as e:
        raise HTTPException(500, f"Integration failed: {str(e)}")


# ============================================================================
# LINKEDIN OAUTH
# ============================================================================

@router.get("/linkedin/authorize")
async def linkedin_authorize(
    workspace_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_oauth_user),
    db: Session = Depends(get_db)
):
    """Initiate LinkedIn OAuth 2.0 flow"""
    from app.models import ClientWorkspace
    result = db.execute(
        select(ClientWorkspace).where(
            ClientWorkspace.id == workspace_id,
            ClientWorkspace.tenant_id == current_user.tenant_id
        )
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(404, "Workspace not found or access denied")
    
    state = create_oauth_state(workspace_id, "linkedin", current_user.user_id)
    client_id, _, redirect_uri = resolve_credentials(workspace_id, "linkedin", db)
    
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid profile email w_member_social",
        "state": state
    }
    
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"
    
    return RedirectResponse(url=auth_url)


@router.get("/callback/linkedin")
async def linkedin_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db)
):
    """Handle LinkedIn OAuth callback"""
    if error:
        raise HTTPException(400, f"LinkedIn authorization failed: {error}")
    
    if not code or not state:
        raise HTTPException(400, "Missing authorization code or state")
    
    oauth_state = verify_oauth_state(state)
    client_id, client_secret, redirect_uri = resolve_credentials(oauth_state["workspace_id"], "linkedin", db)
    
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": client_id,
                    "client_secret": client_secret
                }
            )
            token_response.raise_for_status()
            token_data = token_response.json()
        
        encrypted_token = encrypt_token(token_data["access_token"])
        
        integration = SecureIntegration(
            id=f"int_linkedin_{oauth_state['workspace_id']}",
            workspace_id=oauth_state["workspace_id"],
            platform=IntegrationPlatform.LINKEDIN,
            encrypted_access_token=encrypted_token,
            token_expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 5184000)),
            external_account_id="pending",
            external_account_name="LinkedIn Account",
            is_valid=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        existing = db.execute(
            select(SecureIntegration).where(SecureIntegration.id == integration.id)
        )
        if existing.scalar_one_or_none():
            db.merge(integration)
        else:
            db.add(integration)
        
        db.commit()
        
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/oauth/success?platform=linkedin&workspace_id={oauth_state['workspace_id']}"
        )
        
    except Exception as e:
        raise HTTPException(500, f"Integration failed: {str(e)}")


# ============================================================================
# GOOGLE ADS OAUTH
# ============================================================================

@router.get("/google/authorize")
async def google_authorize(
    workspace_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_oauth_user),
    db: Session = Depends(get_db)
):
    """Initiate Google Ads OAuth flow"""
    from app.models import ClientWorkspace
    result = db.execute(
        select(ClientWorkspace).where(
            ClientWorkspace.id == workspace_id,
            ClientWorkspace.tenant_id == current_user.tenant_id
        )
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(404, "Workspace not found or access denied")
    
    state = create_oauth_state(workspace_id, "google", current_user.user_id)
    client_id, _, redirect_uri = resolve_credentials(workspace_id, "google", db)
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/adwords openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent"
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/callback/google")
async def google_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback"""
    if error:
        raise HTTPException(400, f"Google Ads authorization failed: {error}")
    
    if not code or not state:
        raise HTTPException(400, "Missing authorization code or state")
    
    oauth_state = verify_oauth_state(state)
    client_id, client_secret, redirect_uri = resolve_credentials(oauth_state["workspace_id"], "google", db)
    
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            
        encrypted_token = encrypt_token(token_data["access_token"])
        refresh_token = token_data.get("refresh_token", "")
        encrypted_refresh = encrypt_token(refresh_token) if refresh_token else None
        
        external_account_id = "pending"
        external_account_name = "Google Ads Account"
        
        try:
            async with httpx.AsyncClient() as client:
                info_resp = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {token_data['access_token']}"}
                )
                if info_resp.status_code == 200:
                    info_data = info_resp.json()
                    external_account_id = info_data.get("sub", "pending")
                    external_account_name = info_data.get("email", "Google Ads Account")
        except Exception:
            pass
            
        integration = SecureIntegration(
            id=f"int_google_{oauth_state['workspace_id']}",
            workspace_id=oauth_state["workspace_id"],
            platform=IntegrationPlatform.GOOGLE,
            encrypted_access_token=encrypted_token,
            encrypted_refresh_token=encrypted_refresh,
            token_expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600)),
            external_account_id=external_account_id,
            external_account_name=external_account_name,
            is_valid=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        existing = db.execute(
            select(SecureIntegration).where(SecureIntegration.id == integration.id)
        )
        if existing.scalar_one_or_none():
            db.merge(integration)
        else:
            db.add(integration)
            
        db.commit()
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/oauth/success?platform=google&workspace_id={oauth_state['workspace_id']}"
        )
        
    except Exception as e:
        raise HTTPException(500, f"Integration failed: {str(e)}")


# ============================================================================
# PINTEREST OAUTH
# ============================================================================

@router.get("/pinterest/authorize")
async def pinterest_authorize(
    workspace_id: str,
    request: Request,
    current_user: CurrentUser = Depends(get_oauth_user),
    db: Session = Depends(get_db)
):
    """Initiate Pinterest OAuth flow"""
    from app.models import ClientWorkspace
    result = db.execute(
        select(ClientWorkspace).where(
            ClientWorkspace.id == workspace_id,
            ClientWorkspace.tenant_id == current_user.tenant_id
        )
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(404, "Workspace not found or access denied")
    
    state = create_oauth_state(workspace_id, "pinterest", current_user.user_id)
    client_id, _, redirect_uri = resolve_credentials(workspace_id, "pinterest", db)
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "ads:read,boards:read,pins:read",
        "state": state
    }
    
    auth_url = f"https://www.pinterest.com/oauth/?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/callback/pinterest")
async def pinterest_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db)
):
    """Handle Pinterest OAuth callback"""
    if error:
        raise HTTPException(400, f"Pinterest authorization failed: {error}")
    
    if not code or not state:
        raise HTTPException(400, "Missing authorization code or state")
    
    oauth_state = verify_oauth_state(state)
    client_id, client_secret, redirect_uri = resolve_credentials(oauth_state["workspace_id"], "pinterest", db)
    
    try:
        auth_str = f"{client_id}:{client_secret}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://api.pinterest.com/v5/oauth/token",
                headers={
                    "Authorization": f"Basic {b64_auth}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri
                }
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            
        encrypted_token = encrypt_token(token_data["access_token"])
        refresh_token = token_data.get("refresh_token", "")
        encrypted_refresh = encrypt_token(refresh_token) if refresh_token else None
        
        external_account_id = "pending"
        external_account_name = "Pinterest Account"
        
        try:
            async with httpx.AsyncClient() as client:
                info_resp = await client.get(
                    "https://api.pinterest.com/v5/user_account",
                    headers={"Authorization": f"Bearer {token_data['access_token']}"}
                )
                if info_resp.status_code == 200:
                    info_data = info_resp.json()
                    external_account_id = info_data.get("username", "pending")
                    external_account_name = info_data.get("username", "Pinterest Account")
        except Exception:
            pass
            
        integration = SecureIntegration(
            id=f"int_pinterest_{oauth_state['workspace_id']}",
            workspace_id=oauth_state["workspace_id"],
            platform=IntegrationPlatform.PINTEREST,
            encrypted_access_token=encrypted_token,
            encrypted_refresh_token=encrypted_refresh,
            token_expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 86400)),
            external_account_id=external_account_id,
            external_account_name=external_account_name,
            is_valid=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        existing = db.execute(
            select(SecureIntegration).where(SecureIntegration.id == integration.id)
        )
        if existing.scalar_one_or_none():
            db.merge(integration)
        else:
            db.add(integration)
            
        db.commit()
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/oauth/success?platform=pinterest&workspace_id={oauth_state['workspace_id']}"
        )
        
    except Exception as e:
        raise HTTPException(500, f"Integration failed: {str(e)}")


# ============================================================================
# TOKEN REFRESH ENDPOINTS
# ============================================================================

@router.post("/refresh/{platform}")
async def refresh_token(
    platform: str,
    workspace_id: str,
    current_user: CurrentUser = Depends(get_oauth_user),
    db: Session = Depends(get_db)
):
    """Refresh expired OAuth token"""
    try:
        platform_enum = IntegrationPlatform(platform.lower())
    except ValueError:
        raise HTTPException(400, f"Invalid platform name: {platform}")
        
    result = db.execute(
        select(SecureIntegration).where(
            SecureIntegration.workspace_id == workspace_id,
            SecureIntegration.platform == platform_enum
        )
    )
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(404, "Integration not found")
        
    client_id, client_secret, redirect_uri = resolve_credentials(workspace_id, platform, db)
    
    if platform == "tiktok" and integration.encrypted_refresh_token:
        refresh_token = decrypt_token(integration.encrypted_refresh_token)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://open.tiktokapis.com/v2/oauth/token/",
                json={
                    "client_key": client_id,
                    "client_secret": client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token
                }
            )
            response.raise_for_status()
            token_data = response.json()
            
        integration.encrypted_access_token = encrypt_token(token_data["data"]["access_token"])
        if "refresh_token" in token_data["data"]:
            integration.encrypted_refresh_token = encrypt_token(token_data["data"]["refresh_token"])
        integration.token_expires_at = datetime.utcnow() + timedelta(seconds=token_data["data"].get("expires_in", 86400))
        integration.updated_at = datetime.utcnow()
        db.commit()
        return {"status": "success", "expires_at": integration.token_expires_at.isoformat()}
        
    elif platform == "google" and integration.encrypted_refresh_token:
        refresh_token = decrypt_token(integration.encrypted_refresh_token)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
            )
            response.raise_for_status()
            token_data = response.json()
            
        integration.encrypted_access_token = encrypt_token(token_data["access_token"])
        integration.token_expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))
        integration.updated_at = datetime.utcnow()
        db.commit()
        return {"status": "success", "expires_at": integration.token_expires_at.isoformat()}
        
    elif platform == "pinterest" and integration.encrypted_refresh_token:
        refresh_token = decrypt_token(integration.encrypted_refresh_token)
        auth_str = f"{client_id}:{client_secret}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.pinterest.com/v5/oauth/token",
                headers={
                    "Authorization": f"Basic {b64_auth}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token
                }
            )
            response.raise_for_status()
            token_data = response.json()
            
        integration.encrypted_access_token = encrypt_token(token_data["access_token"])
        integration.token_expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 86400))
        integration.updated_at = datetime.utcnow()
        db.commit()
        return {"status": "success", "expires_at": integration.token_expires_at.isoformat()}
        
    elif platform == "twitter" and integration.encrypted_refresh_token:
        refresh_token = decrypt_token(integration.encrypted_refresh_token)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.twitter.com/2/oauth2/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id
                },
                auth=(client_id, client_secret)
            )
            response.raise_for_status()
            token_data = response.json()
            
        integration.encrypted_access_token = encrypt_token(token_data["access_token"])
        if "refresh_token" in token_data:
            integration.encrypted_refresh_token = encrypt_token(token_data["refresh_token"])
        integration.token_expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 7200))
        integration.updated_at = datetime.utcnow()
        db.commit()
        return {"status": "success", "expires_at": integration.token_expires_at.isoformat()}
        
    else:
        raise HTTPException(400, f"Token refresh not supported or no refresh token for {platform}")


@router.post("/simulate/{platform}")
async def simulate_platform_connection(
    platform: str,
    workspace_id: str = Query(...),
    current_user: CurrentUser = Depends(get_oauth_user),
    db: Session = Depends(get_db)
):
    """
    Simulate connecting a platform via sandbox credentials.
    Saves a mock connection to SecureIntegration in the database.
    """
    from app.auth.dependencies import verify_workspace_access
    await verify_workspace_access(workspace_id, current_user, db)
    
    try:
        platform_enum = IntegrationPlatform(platform.lower())
    except ValueError:
        raise HTTPException(400, f"Invalid platform name: {platform}")
        
    # See if already connected
    stmt = select(SecureIntegration).where(
        SecureIntegration.workspace_id == workspace_id,
        SecureIntegration.platform == platform_enum
    )
    result = db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    # Generate mock account ID/Name based on platform
    mock_id = f"sandbox_{platform.lower()}_{hashlib.sha256(workspace_id.encode()).hexdigest()[:8]}"
    mock_names = {
        "meta": "Sandbox Ads Account",
        "google": "Sandbox Google Ads",
        "tiktok": "Sandbox TikTok Business",
        "linkedin": "Sandbox LinkedIn Ads",
        "twitter": "Sandbox Twitter/X Ads",
        "pinterest": "Sandbox Pinterest Ads"
    }
    mock_name = mock_names.get(platform.lower(), "Sandbox Account")
    
    mock_token = encrypt_token(f"mock_token_{hashlib.sha256(workspace_id.encode()).hexdigest()[:16]}")
    mock_refresh = encrypt_token(f"mock_refresh_{hashlib.sha256(workspace_id.encode()).hexdigest()[:16]}")
    expires_at = datetime.utcnow() + timedelta(days=60)
    
    if existing:
        existing.encrypted_access_token = mock_token
        existing.encrypted_refresh_token = mock_refresh
        existing.token_expires_at = expires_at
        existing.external_account_id = mock_id
        existing.external_account_name = mock_name
        existing.is_valid = True
        existing.updated_at = datetime.utcnow()
    else:
        new_int = SecureIntegration(
            workspace_id=workspace_id,
            platform=platform_enum,
            encrypted_access_token=mock_token,
            encrypted_refresh_token=mock_refresh,
            token_expires_at=expires_at,
            external_account_id=mock_id,
            external_account_name=mock_name,
            scopes="sandbox_all",
            is_valid=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(new_int)
        
    # Log the action
    from app.agents.orchestrator import AgentOrchestrator
    orchestrator = AgentOrchestrator(db, workspace_id)
    orchestrator._log_action(
        "System",
        f"Connected {platform.capitalize()} via Sandbox Simulator",
        "EXECUTED"
    )
    
    db.commit()
    return {"status": "success", "message": f"Successfully simulated sandbox connection for {platform}"}