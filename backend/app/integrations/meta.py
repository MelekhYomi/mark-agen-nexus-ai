"""
Meta (Facebook/Instagram) Integration
Handles all Meta Graph API operations including posting, insights, and ad management.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class MetaIntegration:
    """
    Meta Graph API integration for Facebook and Instagram.
    Supports posting, insights, ad campaigns, and page management.
    """
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}"
        }
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict:
        """Make authenticated request to Meta Graph API"""
        url = f"{self.BASE_URL}/{endpoint}"
        
        if params is None:
            params = {}
        params["access_token"] = self.access_token
        
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                response = await client.get(url, params=params)
            elif method == "POST":
                response = await client.post(url, params=params, json=data)
            elif method == "DELETE":
                response = await client.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
    
    # ========================================================================
    # USER & PAGE OPERATIONS
    # ========================================================================
    
    async def get_user_info(self) -> Dict:
        """Get authenticated user's profile information"""
        return await self._request("GET", "me", params={
            "fields": "id,name,email,picture"
        })
    
    async def get_user_pages(self) -> List[Dict]:
        """Get all Facebook pages the user manages"""
        result = await self._request("GET", "me/accounts")
        return result.get("data", [])
    
    async def get_page_info(self, page_id: str) -> Dict:
        """Get Facebook page information"""
        return await self._request("GET", page_id, params={
            "fields": "id,name,username,followers_count,link"
        })
    
    # ========================================================================
    # POSTING OPERATIONS
    # ========================================================================
    
    async def publish_post(
        self,
        page_id: str,
        message: str,
        link: Optional[str] = None,
        published: bool = True
    ) -> Dict:
        """
        Publish a post to a Facebook page.
        Can be published immediately or scheduled.
        """
        data = {
            "message": message,
            "published": published
        }
        
        if link:
            data["link"] = link
        
        result = await self._request("POST", f"{page_id}/feed", data=data)
        
        return {
            "post_id": result.get("id"),
            "status": "published" if published else "scheduled",
            "url": f"https://facebook.com/{result.get('id')}"
        }
    
    async def publish_instagram_post(
        self,
        ig_user_id: str,
        image_url: str,
        caption: str
    ) -> Dict:
        """Publish a post to Instagram Business account"""
        # Step 1: Create media container
        container_result = await self._request("POST", f"{ig_user_id}/media", data={
            "image_url": image_url,
            "caption": caption
        })
        
        container_id = container_result.get("id")
        
        # Step 2: Publish the container
        publish_result = await self._request("POST", f"{ig_user_id}/media_publish", data={
            "creation_id": container_id
        })
        
        return {
            "post_id": publish_result.get("id"),
            "status": "published"
        }
    
    async def publish_story(
        self,
        page_id: str,
        media_url: str,
        media_type: str = "photo"
    ) -> Dict:
        """Publish a story to Facebook page"""
        data = {
            "source": media_url,
            "media_type": media_type
        }
        
        result = await self._request("POST", f"{page_id}/stories", data=data)
        
        return {
            "story_id": result.get("id"),
            "status": "published"
        }
    
    # ========================================================================
    # INSIGHTS & ANALYTICS
    # ========================================================================
    
    async def get_page_insights(
        self,
        page_id: str,
        metric: str = "page_impressions",
        period: str = "day",
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> Dict:
        """Get Facebook page insights"""
        params = {
            "metric": metric,
            "period": period
        }
        
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        
        return await self._request("GET", f"{page_id}/insights", params=params)
    
    async def get_post_insights(self, post_id: str) -> Dict:
        """Get insights for a specific post"""
        return await self._request("GET", f"{post_id}/insights", params={
            "metric": "post_impressions,post_engagements,post_clicks"
        })
    
    async def get_instagram_insights(
        self,
        ig_user_id: str,
        metric: str = "impressions",
        period: str = "day"
    ) -> Dict:
        """Get Instagram Business account insights"""
        return await self._request("GET", f"{ig_user_id}/insights", params={
            "metric": metric,
            "period": period
        })
    
    # ========================================================================
    # AD CAMPAIGN OPERATIONS
    # ========================================================================
    
    async def get_ad_account(self, ad_account_id: str) -> Dict:
        """Get ad account information"""
        return await self._request("GET", ad_account_id, params={
            "fields": "id,name,account_status,currency,balance"
        })
    
    async def get_campaigns(self, ad_account_id: str) -> List[Dict]:
        """Get all campaigns for an ad account"""
        result = await self._request("GET", f"{ad_account_id}/campaigns", params={
            "fields": "id,name,status,daily_budget,lifetime_budget,objective,created_time",
            "effective_status": ["ACTIVE", "PAUSED", "COMPLETED"]
        })
        return result.get("data", [])
    
    async def get_campaign_insights(
        self,
        campaign_id: str,
        date_preset: str = "last_30d"
    ) -> Dict:
        """Get campaign performance insights"""
        result = await self._request("GET", f"{campaign_id}/insights", params={
            "fields": "impressions,clicks,spend,reach,frequency,ctr,cpc,cpm,actions,website_clicks,conversions",
            "date_preset": date_preset
        })
        
        insights = result.get("data", [{}])
        return insights[0] if insights else {}
    
    async def create_campaign(
        self,
        ad_account_id: str,
        name: str,
        objective: str,
        status: str = "PAUSED",
        daily_budget: Optional[int] = None
    ) -> Dict:
        """Create a new ad campaign"""
        data = {
            "name": name,
            "objective": objective,
            "status": status
        }
        
        if daily_budget:
            data["daily_budget"] = str(daily_budget)
        
        result = await self._request("POST", f"{ad_account_id}/campaigns", data=data)
        
        return {
            "campaign_id": result.get("id"),
            "name": name,
            "status": status
        }
    
    async def update_campaign_budget(
        self,
        campaign_id: str,
        daily_budget: int
    ) -> Dict:
        """Update campaign daily budget (in cents)"""
        result = await self._request("POST", campaign_id, data={
            "daily_budget": str(daily_budget)
        })
        
        return {
            "campaign_id": campaign_id,
            "daily_budget": daily_budget,
            "status": "updated"
        }
    
    async def pause_campaign(self, campaign_id: str) -> Dict:
        """Pause an active campaign"""
        result = await self._request("POST", campaign_id, data={
            "status": "PAUSED"
        })
        
        return {
            "campaign_id": campaign_id,
            "status": "paused"
        }
    
    async def activate_campaign(self, campaign_id: str) -> Dict:
        """Activate a paused campaign"""
        result = await self._request("POST", campaign_id, data={
            "status": "ACTIVE"
        })
        
        return {
            "campaign_id": campaign_id,
            "status": "active"
        }
    
    # ========================================================================
    # ENGAGEMENT OPERATIONS
    # ========================================================================
    
    async def get_post_comments(self, post_id: str) -> List[Dict]:
        """Get comments on a post"""
        result = await self._request("GET", f"{post_id}/comments", params={
            "fields": "id,message,from,created_time,like_count"
        })
        return result.get("data", [])
    
    async def reply_to_comment(self, comment_id: str, message: str) -> Dict:
        """Reply to a comment"""
        result = await self._request("POST", f"{comment_id}/comments", data={
            "message": message
        })
        
        return {
            "reply_id": result.get("id"),
            "status": "posted"
        }
    
    async def like_post(self, post_id: str) -> Dict:
        """Like a post"""
        await self._request("POST", f"{post_id}/likes")
        return {"status": "liked"}
    
    # ========================================================================
    # TOKEN MANAGEMENT
    # ========================================================================
    
    async def get_long_lived_token(self, short_token: str) -> Dict:
        """Exchange short-lived token for long-lived token (60 days)"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": settings.META_APP_ID,
                    "client_secret": settings.META_APP_SECRET,
                    "fb_exchange_token": short_token
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def debug_token(self, token: str) -> Dict:
        """Debug and validate an access token"""
        return await self._request("GET", "debug_token", params={
            "input_token": token
        })