"""
LinkedIn Integration
Handles LinkedIn API operations including posting, profile management, and analytics.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LinkedInIntegration:
    """
    LinkedIn API integration.
    Supports posting, profile management, and company page operations.
    """
    
    BASE_URL = "https://api.linkedin.com/v2"
    SHARE_URL = "https://api.linkedin.com/v2/ugcPosts"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict:
        """Make authenticated request to LinkedIn API"""
        url = f"{self.BASE_URL}/{endpoint}"
        
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                response = await client.get(url, headers=self.headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=self.headers, json=data)
            elif method == "PUT":
                response = await client.put(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = await client.delete(url, headers=self.headers, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
    
    # ========================================================================
    # PROFILE OPERATIONS
    # ========================================================================
    
    async def get_profile(self) -> Dict:
        """Get authenticated user's LinkedIn profile"""
        return await self._request("GET", "me", params={
            "projection": "(id,firstName,lastName,profilePicture(displayImage~:playableStreams))"
        })
    
    async def get_email(self) -> str:
        """Get authenticated user's email address"""
        result = await self._request("GET", "emailAddress", params={
            "q": "members",
            "projection": "(elements*(handle~))"
        })
        
        elements = result.get("elements", [])
        if elements:
            return elements[0].get("handle~", {}).get("emailAddress", "")
        return ""
    
    async def get_connections(self, count: int = 100) -> Dict:
        """Get user's connections"""
        result = await self._request("GET", "connections", params={
            "count": count,
            "start": 0
        })
        
        return {
            "connections": result.get("elements", []),
            "total": result.get("paging", {}).get("total", 0)
        }
    
    # ========================================================================
    # POSTING OPERATIONS
    # ========================================================================
    
    async def create_post(
        self,
        text: str,
        visibility: str = "PUBLIC",
        author_urn: Optional[str] = None
    ) -> Dict:
        """
        Create a post on LinkedIn.
        Can post to personal profile or company page.
        """
        if not author_urn:
            # Get user's URN
            profile = await self.get_profile()
            author_urn = f"urn:li:person:{profile.get('id')}"
        
        post_data = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": visibility
            }
        }
        
        result = await self._request("POST", "ugcPosts", data=post_data)
        
        return {
            "post_urn": result.get("id"),
            "status": "published",
            "visibility": visibility,
            "url": f"https://www.linkedin.com/feed/update/{result.get('id')}"
        }
    
    async def create_image_post(
        self,
        text: str,
        image_url: str,
        image_description: str = "",
        visibility: str = "PUBLIC",
        author_urn: Optional[str] = None
    ) -> Dict:
        """Create a post with an image"""
        if not author_urn:
            profile = await self.get_profile()
            author_urn = f"urn:li:person:{profile.get('id')}"
        
        # Step 1: Register upload
        register_data = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": author_urn,
                "serviceRelationships": [{
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }]
            }
        }
        
        upload_result = await self._request("POST", "assets?action=registerUpload", data=register_data)
        upload_urn = upload_result.get("value", {}).get("asset")
        
        # Step 2: Create post with image
        post_data = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "IMAGE",
                    "media": [{
                        "status": "READY",
                        "description": {
                            "text": image_description
                        },
                        "media": upload_urn,
                        "title": {
                            "text": ""
                        }
                    }]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": visibility
            }
        }
        
        result = await self._request("POST", "ugcPosts", data=post_data)
        
        return {
            "post_urn": result.get("id"),
            "asset_urn": upload_urn,
            "status": "published"
        }
    
    async def create_article_post(
        self,
        title: str,
        text: str,
        article_url: str,
        visibility: str = "PUBLIC",
        author_urn: Optional[str] = None
    ) -> Dict:
        """Create a post with an article link"""
        if not author_urn:
            profile = await self.get_profile()
            author_urn = f"urn:li:person:{profile.get('id')}"
        
        post_data = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "ARTICLE",
                    "media": [{
                        "status": "READY",
                        "originalUrl": article_url,
                        "title": {
                            "text": title
                        }
                    }]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": visibility
            }
        }
        
        result = await self._request("POST", "ugcPosts", data=post_data)
        
        return {
            "post_urn": result.get("id"),
            "status": "published"
        }
    
    async def delete_post(self, post_urn: str) -> Dict:
        """Delete a post"""
        await self._request("DELETE", f"ugcPosts/{post_urn}")
        return {
            "post_urn": post_urn,
            "status": "deleted"
        }
    
    # ========================================================================
    # COMPANY PAGE OPERATIONS
    # ========================================================================
    
    async def get_company_pages(self) -> List[Dict]:
        """Get company pages the user administers"""
        result = await self._request("GET", "organizationalEntityAcls", params={
            "q": "roleAssignee",
            "role": "ADMINISTRATOR",
            "projection": "(elements*(organizationalTarget~(localizedName,vanityName)))"
        })
        
        return result.get("elements", [])
    
    async def post_to_company_page(
        self,
        company_urn: str,
        text: str,
        visibility: str = "PUBLIC"
    ) -> Dict:
        """Post to a company page"""
        post_data = {
            "author": company_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": visibility
            }
        }
        
        result = await self._request("POST", "ugcPosts", data=post_data)
        
        return {
            "post_urn": result.get("id"),
            "company_urn": company_urn,
            "status": "published"
        }
    
    # ========================================================================
    # ANALYTICS OPERATIONS
    # ========================================================================
    
    async def get_post_analytics(self, post_urn: str) -> Dict:
        """Get analytics for a specific post"""
        result = await self._request("GET", "socialActions", params={
            "ids": f"List({post_urn})",
            "projection": "(elements*(totalShareStatistics))"
        })
        
        elements = result.get("elements", [])
        if elements:
            return elements[0].get("totalShareStatistics", {})
        return {}
    
    async def get_profile_views(self, time_range: str = "CURRENT_MONTH") -> Dict:
        """Get profile view statistics"""
        result = await self._request("GET", "organizationAcls", params={
            "q": "roleAssignee",
            "projection": "(elements*(organizationalTarget~(localizedName)))"
        })
        
        # Note: Actual view count requires additional API calls
        return {
            "time_range": time_range,
            "views": 0,
            "note": "Profile views require elevated API access"
        }
    
    # ========================================================================
    # ENGAGEMENT OPERATIONS
    # ========================================================================
    
    async def like_post(self, post_urn: str, actor_urn: Optional[str] = None) -> Dict:
        """Like a post"""
        if not actor_urn:
            profile = await self.get_profile()
            actor_urn = f"urn:li:person:{profile.get('id')}"
        
        like_data = {
            "actor": actor_urn,
            "object": post_urn,
            "reactionType": "LIKE"
        }
        
        await self._request("POST", "socialActions", data=like_data)
        
        return {
            "post_urn": post_urn,
            "status": "liked"
        }
    
    async def comment_on_post(
        self,
        post_urn: str,
        text: str,
        actor_urn: Optional[str] = None
    ) -> Dict:
        """Comment on a post"""
        if not actor_urn:
            profile = await self.get_profile()
            actor_urn = f"urn:li:person:{profile.get('id')}"
        
        comment_data = {
            "actor": actor_urn,
            "object": post_urn,
            "message": {
                "text": text
            }
        }
        
        result = await self._request("POST", "socialActions", data=comment_data)
        
        return {
            "comment_id": result.get("id"),
            "post_urn": post_urn,
            "status": "posted"
        }
    
    async def share_post(
        self,
        post_urn: str,
        text: str = "",
        actor_urn: Optional[str] = None
    ) -> Dict:
        """Share/repost a post"""
        if not actor_urn:
            profile = await self.get_profile()
            actor_urn = f"urn:li:person:{profile.get('id')}"
        
        share_data = {
            "author": actor_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            }
        }
        
        result = await self._request("POST", "ugcPosts", data=share_data)
        
        return {
            "share_urn": result.get("id"),
            "original_post": post_urn,
            "status": "shared"
        }
    
    # ========================================================================
    # NETWORKING OPERATIONS
    # ========================================================================
    
    async def send_connection_request(self, target_urn: str, message: str = "") -> Dict:
        """Send a connection request"""
        invitation_data = {
            "invitee": {
                "com.linkedin.invite.InviteeByProfileUrn": {
                    "profileUrn": target_urn
                }
            },
            "message": message
        }
        
        result = await self._request("POST", "invitations", data=invitation_data)
        
        return {
            "invitation_id": result.get("id"),
            "target_urn": target_urn,
            "status": "sent"
        }
    
    async def get_pending_invitations(self) -> List[Dict]:
        """Get pending connection invitations"""
        result = await self._request("GET", "invitations", params={
            "q": "receivedInvitation",
            "count": 100
        })
        
        return result.get("elements", [])
    
    async def accept_invitation(self, invitation_id: str) -> Dict:
        """Accept a connection invitation"""
        await self._request("PUT", f"invitations/{invitation_id}", data={
            "state": "ACCEPTED"
        })
        
        return {
            "invitation_id": invitation_id,
            "status": "accepted"
        }