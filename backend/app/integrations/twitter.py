"""
Twitter/X Integration
Handles Twitter API v2 operations including tweeting, analytics, and user management.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class TwitterIntegration:
    """
    Twitter API v2 integration.
    Supports tweeting, thread creation, analytics, and engagement.
    """
    
    BASE_URL = "https://api.twitter.com/2"
    
    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict:
        """Make authenticated request to Twitter API"""
        url = f"{self.BASE_URL}/{endpoint}"
        
        async with httpx.AsyncClient(timeout=30) as client:
            if method == "GET":
                response = await client.get(url, headers=self.headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = await client.delete(url, headers=self.headers, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
    
    # ========================================================================
    # USER OPERATIONS
    # ========================================================================
    
    async def get_authenticated_user(self) -> Dict:
        """Get authenticated user's profile information"""
        result = await self._request("GET", "users/me", params={
            "user.fields": "id,name,username,description,profile_image_url,public_metrics,verified"
        })
        return result.get("data", {})
    
    async def get_user_by_username(self, username: str) -> Dict:
        """Get user information by username"""
        result = await self._request("GET", f"users/by/username/{username}", params={
            "user.fields": "id,name,username,description,profile_image_url,public_metrics"
        })
        return result.get("data", {})
    
    async def get_user_followers(
        self,
        user_id: str,
        max_results: int = 100
    ) -> Dict:
        """Get user's followers"""
        result = await self._request("GET", f"users/{user_id}/followers", params={
            "max_results": max_results,
            "user.fields": "id,name,username,profile_image_url"
        })
        
        return {
            "followers": result.get("data", []),
            "total": result.get("meta", {}).get("result_count", 0),
            "next_token": result.get("meta", {}).get("next_token")
        }
    
    async def get_user_following(
        self,
        user_id: str,
        max_results: int = 100
    ) -> Dict:
        """Get users that this user is following"""
        result = await self._request("GET", f"users/{user_id}/following", params={
            "max_results": max_results
        })
        
        return {
            "following": result.get("data", []),
            "total": result.get("meta", {}).get("result_count", 0)
        }
    
    # ========================================================================
    # TWEET OPERATIONS
    # ========================================================================
    
    async def post_tweet(
        self,
        text: str,
        reply_to_tweet_id: Optional[str] = None,
        quote_tweet_id: Optional[str] = None
    ) -> Dict:
        """
        Post a new tweet.
        Can be a regular tweet, reply, or quote tweet.
        """
        data = {"text": text}
        
        if reply_to_tweet_id:
            data["reply"] = {"in_reply_to_tweet_id": reply_to_tweet_id}
        
        if quote_tweet_id:
            data["quote_tweet_id"] = quote_tweet_id
        
        result = await self._request("POST", "tweets", data=data)
        
        return {
            "tweet_id": result.get("data", {}).get("id"),
            "text": text,
            "url": f"https://twitter.com/i/status/{result.get('data', {}).get('id')}"
        }
    
    async def post_thread(self, tweets: List[str]) -> List[Dict]:
        """
        Post a thread of tweets.
        Returns list of tweet IDs in order.
        """
        if not tweets:
            return []
        
        tweet_ids = []
        previous_tweet_id = None
        
        for tweet_text in tweets:
            result = await self.post_tweet(
                tweet_text,
                reply_to_tweet_id=previous_tweet_id
            )
            tweet_ids.append(result["tweet_id"])
            previous_tweet_id = result["tweet_id"]
        
        return tweet_ids
    
    async def get_tweet(self, tweet_id: str) -> Dict:
        """Get a specific tweet"""
        result = await self._request("GET", f"tweets/{tweet_id}", params={
            "tweet.fields": "created_at,public_metrics,conversation_id,lang,source"
        })
        return result.get("data", {})
    
    async def delete_tweet(self, tweet_id: str) -> Dict:
        """Delete a tweet"""
        await self._request("DELETE", f"tweets/{tweet_id}")
        return {
            "tweet_id": tweet_id,
            "status": "deleted"
        }
    
    async def get_user_tweets(
        self,
        user_id: str,
        max_results: int = 10,
        exclude: List[str] = None
    ) -> Dict:
        """Get tweets from a specific user"""
        params = {
            "max_results": max_results,
            "tweet.fields": "created_at,public_metrics,conversation_id"
        }
        
        if exclude:
            params["exclude"] = ",".join(exclude)
        
        result = await self._request("GET", f"users/{user_id}/tweets", params=params)
        
        return {
            "tweets": result.get("data", []),
            "total": result.get("meta", {}).get("result_count", 0)
        }
    
    # ========================================================================
    # ENGAGEMENT OPERATIONS
    # ========================================================================
    
    async def like_tweet(self, user_id: str, tweet_id: str) -> Dict:
        """Like a tweet"""
        await self._request("POST", f"users/{user_id}/likes", data={
            "tweet_id": tweet_id
        })
        
        return {
            "tweet_id": tweet_id,
            "status": "liked"
        }
    
    async def unlike_tweet(self, user_id: str, tweet_id: str) -> Dict:
        """Unlike a tweet"""
        await self._request("DELETE", f"users/{user_id}/likes/{tweet_id}")
        return {
            "tweet_id": tweet_id,
            "status": "unliked"
        }
    
    async def retweet(self, user_id: str, tweet_id: str) -> Dict:
        """Retweet a tweet"""
        await self._request("POST", f"users/{user_id}/retweets", data={
            "tweet_id": tweet_id
        })
        
        return {
            "tweet_id": tweet_id,
            "status": "retweeted"
        }
    
    async def follow_user(self, user_id: str, target_user_id: str) -> Dict:
        """Follow a user"""
        await self._request("POST", f"users/{user_id}/following", data={
            "target_user_id": target_user_id
        })
        
        return {
            "target_user_id": target_user_id,
            "status": "following"
        }
    
    # ========================================================================
    # ANALYTICS OPERATIONS
    # ========================================================================
    
    async def get_tweet_metrics(self, tweet_id: str) -> Dict:
        """Get metrics for a specific tweet"""
        tweet = await self.get_tweet(tweet_id)
        return tweet.get("public_metrics", {})
    
    async def get_user_metrics(self, user_id: str) -> Dict:
        """Get metrics for a user"""
        user = await self._request("GET", f"users/{user_id}", params={
            "user.fields": "public_metrics"
        })
        return user.get("data", {}).get("public_metrics", {})
    
    async def search_tweets(
        self,
        query: str,
        max_results: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Dict:
        """
        Search for tweets matching a query.
        Query supports Twitter search operators.
        """
        params = {
            "query": query,
            "max_results": max_results,
            "tweet.fields": "created_at,public_metrics,author_id"
        }
        
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        
        result = await self._request("GET", "tweets/search/recent", params=params)
        
        return {
            "tweets": result.get("data", []),
            "total": result.get("meta", {}).get("result_count", 0),
            "next_token": result.get("meta", {}).get("next_token")
        }
    
    # ========================================================================
    # TRENDING & DISCOVERY
    # ========================================================================
    
    async def get_trending_topics(self, location_id: str = "1") -> List[Dict]:
        """
        Get trending topics.
        Note: Requires elevated access to Twitter API.
        """
        try:
            result = await self._request("GET", "trends/place", params={
                "id": location_id
            })
            return result.get("trends", [])
        except Exception as e:
            logger.warning(f"Trending topics not available: {e}")
            return []
    
    async def get_hashtag_tweets(
        self,
        hashtag: str,
        max_results: int = 100
    ) -> Dict:
        """Get recent tweets with a specific hashtag"""
        return await self.search_tweets(
            f"#{hashtag}",
            max_results=max_results
        )