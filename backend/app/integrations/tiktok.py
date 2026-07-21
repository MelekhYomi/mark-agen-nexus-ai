"""
TikTok Integration
Handles TikTok API operations including video uploads, analytics, and user management.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class TikTokIntegration:
    """
    TikTok Open API integration.
    Supports video uploads, analytics, and user information.
    """
    
    BASE_URL = "https://open.tiktokapis.com/v2"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict:
        """Make authenticated request to TikTok API"""
        url = f"{self.BASE_URL}/{endpoint}"
        
        async with httpx.AsyncClient(timeout=60) as client:
            if method == "GET":
                response = await client.get(url, headers=self.headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
    
    # ========================================================================
    # USER OPERATIONS
    # ========================================================================
    
    async def get_user_info(self) -> Dict:
        """Get authenticated user's TikTok profile information"""
        result = await self._request("GET", "user/info/", params={
            "fields": "open_id,union_id,avatar_url,display_name,username"
        })
        return result.get("data", {})
    
    async def get_user_stats(self) -> Dict:
        """Get user's follower count and video stats"""
        result = await self._request("GET", "user/stats/", params={
            "fields": "follower_count,following_count,heart_count,video_count,digg_count"
        })
        return result.get("data", {})
    
    # ========================================================================
    # VIDEO OPERATIONS
    # ========================================================================
    
    async def upload_video(
        self,
        video_url: str,
        description: str,
        privacy_level: str = "PUBLIC",
        disable_duet: bool = False,
        disable_stitch: bool = False,
        disable_comment: bool = False
    ) -> Dict:
        """
        Upload a video to TikTok.
        Video must be hosted at a publicly accessible URL.
        """
        data = {
            "post_info": {
                "title": description,
                "privacy_level": privacy_level,
                "disable_duet": disable_duet,
                "disable_stitch": disable_stitch,
                "disable_comment": disable_comment
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url
            }
        }
        
        result = await self._request("POST", "video/upload/", data=data)
        
        return {
            "video_id": result.get("data", {}).get("video_id"),
            "status": result.get("data", {}).get("status"),
            "privacy_level": privacy_level
        }
    
    async def get_video_info(self, video_id: str) -> Dict:
        """Get information about a specific video"""
        result = await self._request("GET", "video/query/", data={
            "filters": {
                "video_ids": [video_id]
            },
            "fields": ["id", "title", "create_time", "cover_image_url", "share_url", "video_duration"]
        })
        
        videos = result.get("data", {}).get("videos", [])
        return videos[0] if videos else {}
    
    async def list_user_videos(
        self,
        max_count: int = 20,
        cursor: int = 0
    ) -> Dict:
        """List videos from authenticated user"""
        result = await self._request("GET", "video/list/", params={
            "max_count": max_count,
            "cursor": cursor
        })
        
        return {
            "videos": result.get("data", {}).get("videos", []),
            "has_more": result.get("data", {}).get("has_more", False),
            "cursor": result.get("data", {}).get("cursor", 0)
        }
    
    async def delete_video(self, video_id: str) -> Dict:
        """Delete a video"""
        await self._request("DELETE", "video/delete/", data={
            "video_id": video_id
        })
        
        return {
            "video_id": video_id,
            "status": "deleted"
        }
    
    # ========================================================================
    # ANALYTICS OPERATIONS
    # ========================================================================
    
    async def get_video_analytics(self, video_id: str) -> Dict:
        """Get analytics for a specific video"""
        result = await self._request("GET", "video/analytics/", params={
            "video_id": video_id
        })
        
        return result.get("data", {})
    
    async def get_user_analytics(
        self,
        start_date: str,
        end_date: str,
        fields: List[str] = None
    ) -> Dict:
        """
        Get user analytics for a date range.
        Fields: video_views, profile_views, followers, likes, comments, shares
        """
        if fields is None:
            fields = ["video_views", "profile_views", "followers", "likes"]
        
        result = await self._request("GET", "analytics/videos/", params={
            "start_date": start_date,
            "end_date": end_date,
            "fields": ",".join(fields)
        })
        
        return result.get("data", {})
    
    async def get_follower_count(self) -> int:
        """Get current follower count"""
        stats = await self.get_user_stats()
        return stats.get("follower_count", 0)
    
    # ========================================================================
    # ENGAGEMENT OPERATIONS
    # ========================================================================
    
    async def get_video_comments(
        self,
        video_id: str,
        max_count: int = 20,
        cursor: int = 0
    ) -> Dict:
        """Get comments on a video"""
        result = await self._request("GET", "video/comment/list/", params={
            "video_id": video_id,
            "max_count": max_count,
            "cursor": cursor
        })
        
        return {
            "comments": result.get("data", {}).get("comments", []),
            "has_more": result.get("data", {}).get("has_more", False),
            "total": result.get("data", {}).get("total", 0)
        }
    
    async def reply_to_comment(
        self,
        video_id: str,
        comment_id: str,
        text: str
    ) -> Dict:
        """Reply to a comment on a video"""
        result = await self._request("POST", "video/comment/reply/", data={
            "video_id": video_id,
            "comment_id": comment_id,
            "text": text
        })
        
        return {
            "reply_id": result.get("data", {}).get("comment_id"),
            "status": "posted"
        }
    
    # ========================================================================
    # TOKEN MANAGEMENT
    # ========================================================================
    
    async def refresh_access_token(self, refresh_token: str) -> Dict:
        """Refresh expired access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/oauth/token/",
                json={
                    "client_key": settings.TIKTOK_APP_ID,
                    "client_secret": settings.TIKTOK_APP_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def get_token_info(self) -> Dict:
        """Get information about current access token"""
        result = await self._request("GET", "oauth/userinfo/")
        return result.get("data", {})