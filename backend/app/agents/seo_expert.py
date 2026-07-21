"""
SEO Expert Agent
Optimizes search engine rankings and drives organic traffic.
"""
import logging
from typing import Dict, List
from datetime import datetime
from app.agents.qwen_client import qwen_client, clean_and_parse_json

logger = logging.getLogger(__name__)


class SEOExpertAgent:
    """Optimizes search engine rankings and organic traffic"""
    
    def __init__(self, db, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
    
    def improve_rankings(self) -> Dict:
        """
        Analyze SEO performance and provide actionable recommendations
        to improve search rankings and organic traffic.
        """
        prompt = """You are an SEO expert with 10+ years experience ranking websites on page 1 of Google.

Analyze SEO performance and provide comprehensive recommendations:

**1. Keyword Opportunities**
- 5 high-volume, low-competition keywords to target
- Current ranking (if any)
- Search volume estimate
- Difficulty score
- Recommended content type

**2. On-Page Optimization**
- Title tag improvements
- Meta description suggestions
- Header structure recommendations
- Internal linking opportunities
- Image optimization suggestions

**3. Content Gaps**
- 3 topics competitors rank for that we don't
- Content brief for each gap
- Estimated traffic potential

**4. Technical SEO**
- Site speed improvements
- Mobile optimization
- Schema markup opportunities
- Crawlability issues

**5. Backlink Strategy**
- 5 high-authority sites to target for backlinks
- Outreach angle for each
- Expected domain authority impact

**6. Quick Wins**
- 3 changes that can be made today for immediate impact
- Expected ranking improvement for each

Return as structured JSON with priorities (high/medium/low)."""

        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a senior SEO consultant who has ranked 1000+ websites on page 1 of Google. You focus on white-hat, sustainable strategies."},
            {"role": "user", "content": prompt}
        ])
        
        recommendations_raw = response["choices"][0]["message"]["content"]
        recommendations = clean_and_parse_json(recommendations_raw)
        thinking = response["choices"][0]["message"].get("reasoning_content", "")
        
        priority_cnt = str(recommendations_raw).count('"priority": "high"')
        
        return {
            "recommendations": recommendations,
            "thinking": thinking,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0),
            "analyzed_at": datetime.utcnow().isoformat(),
            "priority_actions": priority_cnt
        }
    
    def keyword_research(self, niche: str, seed_keywords: List[str]) -> Dict:
        """Research keywords for a specific niche"""
        seeds = ", ".join(seed_keywords)
        
        prompt = f"""Research keywords for the niche: {niche}

Seed keywords: {seeds}

For each keyword provide:
- keyword: the search term
- search_volume: monthly searches (estimate)
- difficulty: 0-100 (how hard to rank)
- cpc: cost per click (estimate)
- intent: informational/navigational/transactional
- content_type: blog post/landing page/product page

Return top 20 keywords sorted by opportunity (high volume, low difficulty)."""
        
        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a keyword research expert using tools like Ahrefs and SEMrush"},
            {"role": "user", "content": prompt}
        ])
        
        keywords_raw = response["choices"][0]["message"]["content"]
        keywords = clean_and_parse_json(keywords_raw)
        
        return {
            "keywords": keywords,
            "niche": niche,
            "seed_keywords": seed_keywords,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0)
        }
    
    def audit_content(self, url: str, target_keyword: str) -> Dict:
        """Audit a webpage for SEO optimization"""
        prompt = f"""Audit this webpage for SEO:
URL: {url}
Target Keyword: {target_keyword}

Provide:
1. Overall SEO score (0-100)
2. Title tag analysis (length, keyword inclusion)
3. Meta description analysis
4. Content quality assessment
5. Keyword density
6. Internal linking score
7. Image optimization
8. Mobile-friendliness
9. Page speed factors
10. Top 5 specific improvements with expected impact

Return as structured JSON."""
        
        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a technical SEO auditor"},
            {"role": "user", "content": prompt}
        ])
        
        audit_raw = response["choices"][0]["message"]["content"]
        audit = clean_and_parse_json(audit_raw)
        
        return {
            "audit": audit,
            "url": url,
            "target_keyword": target_keyword,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0)
        }
    
    def generate_meta_tags(self, page_title: str, content_summary: str, target_keyword: str) -> Dict:
        """Generate SEO-optimized meta title and description"""
        prompt = f"""Create SEO-optimized meta tags:

Page Topic: {page_title}
Content Summary: {content_summary}
Target Keyword: {target_keyword}

Provide:
1. meta_title: Max 60 characters, includes keyword, compelling
2. meta_description: Max 160 characters, includes keyword, has CTA
3. og_title: Open Graph title (similar to meta title)
4. og_description: Open Graph description
5. twitter_card: summary_large_image or summary

Return as JSON object."""
        
        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are an SEO copywriter who writes high-CTR meta tags"},
            {"role": "user", "content": prompt}
        ])
        
        meta_tags_raw = response["choices"][0]["message"]["content"]
        meta_tags = clean_and_parse_json(meta_tags_raw)
        
        return {
            "meta_tags": meta_tags,
            "target_keyword": target_keyword,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0)
        }
    
    def content_optimization(self, content: str, target_keyword: str) -> Dict:
        """Optimize existing content for better rankings"""
        prompt = f"""Optimize this content for the keyword: {target_keyword}

Content:
{content[:2000]}  # Limit to first 2000 chars

Provide:
1. Keyword density analysis (current vs recommended)
2. Suggested keyword placements
3. Header structure improvements
4. Internal linking suggestions
5. Content length recommendation
6. Readability improvements
7. LSI keywords to add
8. Specific sentences to rewrite

Return as structured JSON."""
        
        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a content optimization specialist"},
            {"role": "user", "content": prompt}
        ])
        
        optimizations_raw = response["choices"][0]["message"]["content"]
        optimizations = clean_and_parse_json(optimizations_raw)
        
        return {
            "optimizations": optimizations,
            "target_keyword": target_keyword,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0)
        }