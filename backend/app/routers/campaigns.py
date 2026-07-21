"""
Campaigns Router
Handles ad campaign creation, management, optimization, and analytics.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ClientWorkspace
from app.auth.dependencies import get_current_user, CurrentUser, verify_workspace_access
from app.agents.ads_manager import AdsManagerAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.get("/list")
async def list_campaigns(
    workspace_id: str,
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all ad campaigns for a workspace.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    # In production, would fetch from DB or platform API
    return {
        "status": "success",
        "workspace_id": workspace_id,
        "campaigns": []
    }


@router.post("/create")
async def create_campaign(
    workspace_id: str,
    platform: str = Query(..., description="Platform: meta, google, tiktok, linkedin"),
    objective: str = Query(..., description="Campaign objective: awareness, traffic, conversions, sales"),
    budget: float = Query(..., description="Daily budget in USD"),
    targeting: Optional[Dict[str, Any]] = Body(None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new ad campaign.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    agent = AdsManagerAgent(db, workspace_id)
    result = agent.create_campaign(
        platform=platform,
        objective=objective,
        budget=budget,
        targeting=targeting or {}
    )
    
    return {
        "status": "success",
        "campaign": result
    }


@router.post("/optimize")
async def optimize_campaigns(
    workspace_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Optimize existing campaigns using AI analysis.
    Identifies underperformers and suggests budget reallocations.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    agent = AdsManagerAgent(db, workspace_id)
    result = agent.optimize_campaigns()
    
    return {
        "status": "success",
        "workspace_id": workspace_id,
        "optimizations": result.get("optimizations", []),
        "num_recommendations": result.get("num_recommendations", 0),
        "analyzed_at": result.get("analyzed_at")
    }


@router.post("/{campaign_id}/adjust-budget")
async def adjust_campaign_budget(
    campaign_id: str,
    workspace_id: str,
    new_budget: float = Query(..., description="New daily budget in USD"),
    reason: Optional[str] = Query(None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Adjust campaign budget.
    Requires approval if change is significant.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    agent = AdsManagerAgent(db, workspace_id)
    result = agent.adjust_budget(campaign_id, new_budget, reason)
    
    return {
        "status": "success",
        "updated": result
    }


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    workspace_id: str,
    reason: str = Query("Manual pause", description="Reason for pausing"),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Pause an active campaign.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    agent = AdsManagerAgent(db, workspace_id)
    result = agent.pause_campaign(campaign_id, reason)
    
    return {
        "status": "success",
        "paused": result
    }


@router.post("/{campaign_id}/activate")
async def activate_campaign(
    campaign_id: str,
    workspace_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Activate a paused campaign.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    # In production, would call platform API to activate
    return {
        "status": "success",
        "campaign_id": campaign_id,
        "status": "active"
    }


@router.post("/generate-copy")
async def generate_ad_copy(
    workspace_id: str,
    product: str = Query(...),
    audience: str = Query(...),
    platform: str = Query(...),
    angle: str = Query("benefits", description="Copy angle: benefits, features, social_proof, urgency"),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate ad copy variations using AI.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    agent = AdsManagerAgent(db, workspace_id)
    result = agent.generate_ad_copy(product, audience, platform, angle)
    
    return {
        "status": "success",
        "variations": result.get("variations", []),
        "platform": platform,
        "product": product
    }


@router.get("/{campaign_id}/insights")
async def get_campaign_insights(
    campaign_id: str,
    workspace_id: str,
    date_preset: str = Query("last_30d", description="Date range: today, yesterday, last_7d, last_30d, this_month"),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get campaign performance insights.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    # In production, would fetch from platform API
    return {
        "status": "success",
        "campaign_id": campaign_id,
        "insights": {
            "impressions": 0,
            "clicks": 0,
            "spend": 0,
            "conversions": 0,
            "roas": 0,
            "ctr": 0,
            "cpa": 0
        },
        "date_preset": date_preset
    }


@router.post("/budget-allocation")
async def recommend_budget_allocation(
    workspace_id: str,
    total_budget: float = Query(..., description="Total budget to allocate"),
    campaigns: Optional[List[Dict]] = Body(None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-powered budget allocation recommendations across campaigns.
    """
    await verify_workspace_access(workspace_id, current, db)
    
    agent = AdsManagerAgent(db, workspace_id)
    result = agent.recommend_budget_allocation(campaigns or [], total_budget)
    
    return {
        "status": "success",
        "allocation": result.get("allocation", []),
        "total_budget": total_budget
    }