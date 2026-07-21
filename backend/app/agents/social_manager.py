"""
Social Manager Agent
Handles content creation, scheduling, and publishing across social platforms.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from app.agents.qwen_client import qwen_client, clean_and_parse_json

logger = logging.getLogger(__name__)


class SocialManagerAgent:
    """Manages social media content creation and posting"""
    
    def __init__(self, db, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
    
    def generate_content_suggestions(self, num_suggestions: int = 5) -> Dict:
        """
        Generate content ideas based on trends, brand voice, and platform best practices.
        Returns structured JSON with titles, platforms, content types, and risk scores.
        """
        prompt = f"""You are a world-class social media manager for a brand.

Generate {num_suggestions} high-quality content suggestions. For each suggestion, provide:
1. title: Catchy headline (max 60 chars)
2. platform: Instagram, TikTok, LinkedIn, Twitter, or Facebook
3. content_type: image, video, carousel, story, or text
4. description: Brief description of the content (2-3 sentences)
5. caption: Ready-to-use caption with emojis
6. hashtags: 5-10 relevant hashtags
7. best_time_to_post: Optimal posting time
8. risk_score: 0.0-1.0 (how controversial/risky this content is)

Current trends to consider:
- Short-form video is dominating
- Authentic, behind-the-scenes content performs well
- Educational content gets high engagement
- User-generated content builds trust

Return as a JSON array. Each item must have all 8 fields."""

        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a creative social media expert with 10+ years experience. You understand what content performs well on each platform."},
            {"role": "user", "content": prompt}
        ])
        
        content = response["choices"][0]["message"]["content"]
        content_parsed = clean_and_parse_json(content)
        thinking = response["choices"][0]["message"].get("reasoning_content", "")
        
        return {
            "suggestions": content_parsed,
            "thinking": thinking,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0),
            "timestamp": datetime.utcnow().isoformat(),
            "num_suggestions": num_suggestions
        }
    
    def create_post(
        self, 
        platform: str, 
        content: str, 
        media_urls: Optional[List[str]] = None,
        scheduled_time: Optional[str] = None
    ) -> Dict:
        """Create a social media post (draft or scheduled)"""
        return {
            "post_id": f"post_{datetime.utcnow().timestamp()}",
            "platform": platform,
            "content": content,
            "media_urls": media_urls or [],
            "scheduled_time": scheduled_time,
            "status": "scheduled" if scheduled_time else "draft",
            "created_at": datetime.utcnow().isoformat()
        }
    
    def publish_post(self, post_data: Dict) -> Dict:
        """Publish a post to social media (requires integration)"""
        platform = post_data.get('platform')
        
        # In production, this would call the actual platform API
        # For now, return success with mock data
        return {
            "post_id": post_data.get('post_id'),
            "platform": platform,
            "status": "published",
            "published_at": datetime.utcnow().isoformat(),
            "url": f"https://{platform}.com/post/{post_data.get('post_id')}"
        }
    
    def analyze_engagement(self, platform: str, post_id: str) -> Dict:
        """Analyze post engagement metrics"""
        # Mock data - in production, fetch from platform API
        return {
            "platform": platform,
            "post_id": post_id,
            "metrics": {
                "likes": 247,
                "comments": 34,
                "shares": 18,
                "saves": 56,
                "reach": 8420,
                "impressions": 12340,
                "engagement_rate": 4.2
            },
            "top_comment": "This is amazing! 🔥",
            "sentiment": "positive"
        }
    
    def generate_hashtags(self, topic: str, platform: str, count: int = 10) -> List[str]:
        """Generate relevant hashtags for a topic"""
        prompt = f"Generate {count} trending hashtags for a {platform} post about: {topic}. Return as a comma-separated list."
        
        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a hashtag expert"},
            {"role": "user", "content": prompt}
        ])
        
        hashtags = response["choices"][0]["message"]["content"].split(',')
        return [h.strip() for h in hashtags if h.strip()]
    
    def content_calendar(self, days: int = 7) -> Dict:
        """Generate a content calendar for the next N days"""
        prompt = f"""Create a {days}-day content calendar with one post per day.
For each day, provide:
- date: YYYY-MM-DD format
- platform: which platform to post on
- content_type: image/video/carousel/story
- topic: what the post is about
- caption_hook: first line of caption to grab attention

Return as JSON array."""
        
        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a content strategist"},
            {"role": "user", "content": prompt}
        ])
        
        calendar_raw = response["choices"][0]["message"]["content"]
        calendar_parsed = clean_and_parse_json(calendar_raw)
        
        return {
            "calendar": calendar_parsed,
            "days": days,
            "generated_at": datetime.utcnow().isoformat()
        }