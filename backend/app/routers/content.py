"""
Content Router
Handles content creation, scheduling, and publishing across social platforms.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ClientWorkspace, ContentCalendarItem, ApprovalStatus, IntegrationPlatform
from app.auth.dependencies import get_current_user, CurrentUser, verify_workspace_access
from app.agents.social_manager import SocialManagerAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["Content"])


@router.post("/generate")
async def generate_content(
    workspace_id: str,
    topic: str = Query(..., description="Content topic or theme"),
    platform: str = Query(..., description="Target platform: instagram, tiktok, linkedin, twitter, facebook"),
    num_suggestions: int = Query(5, ge=1, le=10),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate content suggestions using AI.
    Returns multiple content ideas with captions, hashtags, and risk scores.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    agent = SocialManagerAgent(db, workspace_id)
    result = agent.generate_content_suggestions(num_suggestions)
    
    return {
        "status": "success",
        "workspace_id": workspace_id,
        "topic": topic,
        "platform": platform,
        "suggestions": result.get("suggestions", []),
        "tokens_used": result.get("tokens_used", 0),
        "generated_at": result.get("timestamp")
    }


@router.post("/create")
async def create_post(
    workspace_id: str,
    platform: str = Query(...),
    content: str = Query(...),
    media_urls: Optional[List[str]] = Query(None),
    scheduled_time: Optional[str] = Query(None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new social media post (draft or scheduled).
    """
    await verify_workspace_access(workspace_id, current, db)
    
    agent = SocialManagerAgent(db, workspace_id)
    result = agent.create_post(
        platform=platform,
        content=content,
        media_urls=media_urls,
        scheduled_time=scheduled_time
    )
    
    return {
        "status": "success",
        "post": result
    }


@router.post("/publish")
async def publish_post(
    post_id: str,
    workspace_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Publish a post to social media.
    Requires integration to be connected.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    # In production, would fetch post from DB and publish via integration
    return {
        "status": "success",
        "post_id": post_id,
        "published_at": datetime.utcnow().isoformat()
    }


@router.get("/calendar")
async def get_content_calendar(
    workspace_id: str,
    days: int = Query(7, ge=1, le=30),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a content calendar for the next N days.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    agent = SocialManagerAgent(db, workspace_id)
    result = agent.content_calendar(days)
    
    return {
        "status": "success",
        "calendar": result.get("calendar", []),
        "days": days
    }


@router.get("/calendar/items")
async def get_db_calendar_items(
    workspace_id: str,
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all database-backed content calendar items for a workspace.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    query = select(ContentCalendarItem).where(
        ContentCalendarItem.workspace_id == workspace_id
    )
    
    if status_filter:
        try:
            status_enum = ApprovalStatus(status_filter.lower())
            query = query.where(ContentCalendarItem.status == status_enum)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status_filter}")
            
    query = query.order_by(ContentCalendarItem.scheduled_time.asc())
    result = db.execute(query)
    items = result.scalars().all()
    
    return {
        "status": "success",
        "items": [
            {
                "id": item.id,
                "workspace_id": item.workspace_id,
                "platform": item.platform.value,
                "scheduled_time": item.scheduled_time.isoformat(),
                "title": item.title,
                "content_draft": item.content_draft,
                "media_type": item.media_type,
                "media_generation_prompt": item.media_generation_prompt,
                "media_url": item.media_url,
                "status": item.status.value,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat()
            }
            for item in items
        ]
    }


@router.put("/calendar/items/{item_id}")
async def update_calendar_item(
    item_id: str,
    payload: Dict[str, Any] = Body(...),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update/edit a content calendar item's properties.
    This enables the user to edit and approve the calendar item till it satisfies.
    """
    result = db.execute(
        select(ContentCalendarItem).where(ContentCalendarItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(404, "Calendar item not found")
        
    await verify_workspace_access(item.workspace_id, current, db)
    
    # Update fields if provided
    if "title" in payload:
        item.title = payload["title"]
    if "content_draft" in payload:
        item.content_draft = payload["content_draft"]
    if "scheduled_time" in payload:
        try:
            item.scheduled_time = datetime.fromisoformat(payload["scheduled_time"])
        except ValueError:
            raise HTTPException(400, "Invalid scheduled_time format. Use ISO format.")
    if "platform" in payload:
        try:
            item.platform = IntegrationPlatform(payload["platform"].lower())
        except ValueError:
            raise HTTPException(400, f"Invalid platform: {payload['platform']}")
    if "media_type" in payload:
        item.media_type = payload["media_type"].upper()
    if "media_url" in payload:
        item.media_url = payload["media_url"]
    if "media_generation_prompt" in payload:
        item.media_generation_prompt = payload["media_generation_prompt"]
    if "status" in payload:
        try:
            item.status = ApprovalStatus(payload["status"].lower())
        except ValueError:
            raise HTTPException(400, f"Invalid status: {payload['status']}")
            
    db.commit()
    
    return {
        "status": "success",
        "item": {
            "id": item.id,
            "workspace_id": item.workspace_id,
            "platform": item.platform.value,
            "scheduled_time": item.scheduled_time.isoformat(),
            "title": item.title,
            "content_draft": item.content_draft,
            "media_type": item.media_type,
            "media_generation_prompt": item.media_generation_prompt,
            "media_url": item.media_url,
            "status": item.status.value
        }
    }


@router.post("/calendar/items/{item_id}/approve")
async def approve_calendar_item(
    item_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve a content calendar item.
    """
    result = db.execute(
        select(ContentCalendarItem).where(ContentCalendarItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(404, "Calendar item not found")
        
    await verify_workspace_access(item.workspace_id, current, db)
    
    item.status = ApprovalStatus.APPROVED
    db.commit()
    
    return {
        "status": "success",
        "item_id": item_id,
        "status_value": item.status.value
    }


@router.post("/calendar/items/{item_id}/reject")
async def reject_calendar_item(
    item_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reject a content calendar item.
    """
    result = db.execute(
        select(ContentCalendarItem).where(ContentCalendarItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(404, "Calendar item not found")
        
    await verify_workspace_access(item.workspace_id, current, db)
    
    item.status = ApprovalStatus.REJECTED
    db.commit()
    
    return {
        "status": "success",
        "item_id": item_id,
        "status_value": item.status.value
    }


@router.post("/hashtags")
async def generate_hashtags(
    workspace_id: str,
    topic: str = Query(...),
    platform: str = Query(...),
    count: int = Query(10, ge=5, le=30),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate relevant hashtags for a topic.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    agent = SocialManagerAgent(db, workspace_id)
    hashtags = agent.generate_hashtags(topic, platform, count)
    
    return {
        "status": "success",
        "topic": topic,
        "platform": platform,
        "hashtags": hashtags
    }


@router.get("/engagement/{post_id}")
async def get_post_engagement(
    post_id: str,
    platform: str = Query(...),
    workspace_id: str = Query(...),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get engagement metrics for a specific post.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    agent = SocialManagerAgent(db, workspace_id)
    metrics = agent.analyze_engagement(platform, post_id)
    
    return {
        "status": "success",
        "post_id": post_id,
        "platform": platform,
        "metrics": metrics
    }