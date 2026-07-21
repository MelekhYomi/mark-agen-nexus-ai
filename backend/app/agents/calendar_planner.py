"""
Content Calendar & Scheduler Agent
Backed by Qwen, plans custom calendars for users' niches and registers them in ContentCalendarItem table.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import select
from app.agents.qwen_client import qwen_client, clean_and_parse_json
from app.models import ContentCalendarItem, ApprovalStatus, IntegrationPlatform

logger = logging.getLogger(__name__)


class CalendarPlannerAgent:
    """Plans customized multi-day content calendars and persists them in the DB as pending approval."""
    
    def __init__(self, db, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        
    def plan_content_calendar(self, niche_strategy: str, days: int = 3) -> Dict[str, Any]:
        """
        Generates a content calendar for N days based on industry/niche strategy.
        Inserts generated items into `content_calendar_items` as PENDING items.
        """
        prompt = f"""You are an elite, senior Content Calendar & Strategist AI.
Your task is to plan a highly optimized, day-by-day content calendar for the next {days} days.
The user's niche or platform strategy is: "{niche_strategy}"

Ensure you generate a balanced mix of media types (TEXT, IMAGE, AUDIO, VIDEO) across different platforms (linkedin, twitter, meta, youtube).
Make sure each calendar item contains high-value topics and realistic angles.

For each day (relative_day from 1 to {days}), provide:
1. platform: string ('linkedin', 'twitter', 'meta', or 'youtube')
2. relative_day: integer (1 for tomorrow, 2 for day after, etc.)
3. hour_of_day: integer (0 to 23, the best hour to post)
4. title: string (catchy, descriptive title for the post, max 100 chars)
5. topic_focus: string (e.g., 'Product Spotlight', 'Industry Commentary', 'Educational Tutorial')
6. media_type: string ('TEXT', 'IMAGE', 'AUDIO', or 'VIDEO')
7. content_angle: string (a paragraph of instructions/description of what the content is about)

Perform the strategic planning and return a JSON object with:
- niche_strategy: string (brief summary of the planned campaign strategy)
- calendar_items: list of items containing the 7 fields above.

Ensure the output is strictly valid JSON."""

        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a content calendar strategist with 15+ years experience planning campaigns for top-tier global brands."},
            {"role": "user", "content": prompt}
        ])
        
        raw_content = response["choices"][0]["message"]["content"]
        parsed = clean_and_parse_json(raw_content)
        thinking = response["choices"][0]["message"].get("reasoning_content", "")
        
        # Parse items and save to DB as ContentCalendarItem
        items_saved = []
        now = datetime.utcnow()
        
        calendar_items = parsed.get("calendar_items", [])
        if isinstance(calendar_items, list):
            for item in calendar_items:
                try:
                    rel_day = int(item.get("relative_day", 1))
                    hour = int(item.get("hour_of_day", 12))
                    scheduled_time = now + timedelta(days=rel_day)
                    scheduled_time = scheduled_time.replace(hour=hour, minute=0, second=0, microsecond=0)
                    
                    platform_str = str(item.get("platform", "linkedin")).lower()
                    # Map to IntegrationPlatform enum values safely
                    platform_enum = IntegrationPlatform.LINKEDIN
                    if "twitter" in platform_str:
                        platform_enum = IntegrationPlatform.TWITTER
                    elif "meta" in platform_str:
                        platform_enum = IntegrationPlatform.META
                    elif "youtube" in platform_str:
                        platform_enum = IntegrationPlatform.YOUTUBE
                    
                    content_draft = f"Draft content for {item.get('title')}: {item.get('content_angle')}"
                    
                    # Formulate media prompt if it's not text
                    media_type = str(item.get("media_type", "TEXT")).upper()
                    media_generation_prompt = None
                    if media_type != "TEXT":
                        media_generation_prompt = f"Design a beautiful {media_type.lower()} asset showcasing: {item.get('title')}. Dynamic lighting, professional layout, styled specifically for {platform_str}."
                    
                    db_item = ContentCalendarItem(
                        workspace_id=self.workspace_id,
                        platform=platform_enum,
                        scheduled_time=scheduled_time,
                        title=item.get("title", "Untitled Scheduled Post"),
                        content_draft=content_draft,
                        media_type=media_type,
                        media_generation_prompt=media_generation_prompt,
                        status=ApprovalStatus.PENDING
                    )
                    self.db.add(db_item)
                    items_saved.append({
                        "platform": platform_enum.value,
                        "scheduled_time": scheduled_time.isoformat(),
                        "title": db_item.title,
                        "media_type": db_item.media_type
                    })
                except Exception as ex:
                    logger.warning(f"Failed to parse or save content calendar item: {item}. Error: {ex}")
            
            self.db.commit()
            
        return {
            "status": "success",
            "niche_strategy": parsed.get("niche_strategy", niche_strategy),
            "calendar_items_count": len(items_saved),
            "saved_items": items_saved,
            "thinking": thinking,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0)
        }
