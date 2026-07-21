"""
Analytics Agent
Tracks performance metrics, generates insights, and provides data-driven recommendations.
"""
import logging
from typing import Dict, List
from datetime import datetime, timedelta
from app.agents.qwen_client import qwen_client, clean_and_parse_json

logger = logging.getLogger(__name__)


class AnalyticsAgent:
    """Tracks and analyzes performance metrics across all channels"""
    
    def __init__(self, db, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
    
    def analyze_performance(self, period: str = "last_30_days") -> Dict:
        """
        Comprehensive performance analysis across all marketing channels.
        Identifies trends, anomalies, and actionable insights.
        """
        prompt = f"""You are a marketing data analyst. Analyze performance data for the {period} period.

**Metrics to Analyze:**
1. **Social Media Performance**
   - Follower growth rate
   - Engagement rate trends
   - Top performing content
   - Worst performing content
   - Best posting times

2. **Website Traffic**
   - Total visitors
   - Traffic sources breakdown
   - Bounce rate
   - Average session duration
   - Top landing pages

3. **Ad Campaign Performance**
   - Total spend
   - ROAS (Return on Ad Spend)
   - CTR (Click-Through Rate)
   - CPA (Cost Per Acquisition)
   - Conversion rate

4. **SEO Performance**
   - Organic traffic
   - Keyword rankings
   - Domain authority
   - Backlink growth

5. **Email Marketing**
   - Open rate
   - Click rate
   - Unsubscribe rate
   - Revenue per email

**Provide:**
- 5 key insights (what the data tells us)
- 3 anomalies (unusual patterns to investigate)
- 5 actionable recommendations (specific next steps)
- 1 forecast (what to expect next month)

Return as structured JSON."""

        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a senior marketing analyst who turns data into actionable business insights. You're honest about problems and optimistic about opportunities."},
            {"role": "user", "content": prompt}
        ])
        
        insights_raw = response["choices"][0]["message"]["content"]
        insights = clean_and_parse_json(insights_raw)
        thinking = response["choices"][0]["message"].get("reasoning_content", "")
        
        insights_cnt = str(insights_raw).count('"insight"')
        
        return {
            "insights": insights,
            "thinking": thinking,
            "period": period,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0),
            "analyzed_at": datetime.utcnow().isoformat(),
            "insights_count": insights_cnt
        }
    
    def generate_report(self, period: str = "weekly", format: str = "executive") -> Dict:
        """Generate a comprehensive performance report"""
        prompt = f"""Generate a {format}-level {period} marketing performance report.

Include:
1. Executive Summary (3-5 sentences)
2. Key Metrics Dashboard (with % changes)
3. Channel Performance Breakdown
4. Top Wins (what worked well)
5. Areas for Improvement (what didn't work)
6. Recommendations for Next Period
7. Budget Utilization
8. ROI Calculation

Make it concise, data-driven, and actionable.
Return as structured JSON."""
        
        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a marketing reporting expert who creates clear, executive-ready reports"},
            {"role": "user", "content": prompt}
        ])
        
        report_raw = response["choices"][0]["message"]["content"]
        report = clean_and_parse_json(report_raw)
        
        return {
            "report": report,
            "period": period,
            "format": format,
            "generated_at": datetime.utcnow().isoformat(),
            "tokens_used": response.get("usage", {}).get("total_tokens", 0)
        }
    
    def track_kpis(self, kpis: List[Dict]) -> Dict:
        """Track key performance indicators and alert on anomalies"""
        prompt = f"""Analyze these KPIs and identify any that need attention:

{kpis}

For each KPI:
- current_value
- target_value
- variance (%)
- status: on_track/at_risk/off_track
- action_required: yes/no
- recommended_action (if needed)

Flag any KPIs that are off-track and need immediate attention.
Return as JSON."""
        
        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a KPI monitoring specialist"},
            {"role": "user", "content": prompt}
        ])
        
        analysis_raw = response["choices"][0]["message"]["content"]
        kpi_analysis = clean_and_parse_json(analysis_raw)
        
        return {
            "kpi_analysis": kpi_analysis,
            "kpis_tracked": len(kpis),
            "alerts": str(analysis_raw).count('"status": "off_track"'),
            "tokens_used": response.get("usage", {}).get("total_tokens", 0)
        }
    
    def forecast_growth(self, months: int = 3, current_metrics: Dict = None) -> Dict:
        """Forecast future growth based on current trends"""
        prompt = f"""Based on current performance trends, forecast growth for the next {months} months.

Current metrics:
{current_metrics or 'Not provided - use industry benchmarks'}

Provide forecasts for:
1. Follower growth (by platform)
2. Website traffic
3. Revenue/conversions
4. Ad performance (ROAS trend)
5. Email list growth

For each forecast:
- projected_value
- confidence_level (low/medium/high)
- key_assumptions
- risks_to_forecast

Return as structured JSON."""
        
        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a growth forecasting analyst. Be realistic and conservative in your projections."},
            {"role": "user", "content": prompt}
        ])
        
        forecast_raw = response["choices"][0]["message"]["content"]
        forecast = clean_and_parse_json(forecast_raw)
        
        return {
            "forecast": forecast,
            "months": months,
            "generated_at": datetime.utcnow().isoformat(),
            "tokens_used": response.get("usage", {}).get("total_tokens", 0)
        }
    
    def cohort_analysis(self, user_data: List[Dict]) -> Dict:
        """Perform cohort analysis to understand user behavior"""
        prompt = f"""Analyze this user cohort data:

{user_data}

Provide:
1. Retention rates by cohort
2. Lifetime value by acquisition channel
3. Engagement patterns
4. Churn indicators
5. Recommendations to improve retention

Return as JSON."""
        
        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a user analytics expert specializing in cohort analysis"},
            {"role": "user", "content": prompt}
        ])
        
        analysis_raw = response["choices"][0]["message"]["content"]
        analysis = clean_and_parse_json(analysis_raw)
        
        return {
            "analysis": analysis,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0)
        }
    
    def ab_test_analysis(self, test_data: Dict) -> Dict:
        """Analyze A/B test results for statistical significance"""
        prompt = f"""Analyze this A/B test data:

{test_data}

Provide:
1. Statistical significance (p-value)
2. Winner declaration
3. Confidence level
4. Recommended action
5. Sample size adequacy
6. Next test recommendations

Return as JSON."""
        
        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a statistical analyst specializing in marketing experiments"},
            {"role": "user", "content": prompt}
        ])
        
        analysis_raw = response["choices"][0]["message"]["content"]
        analysis = clean_and_parse_json(analysis_raw)
        
        return {
            "analysis": analysis,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0)
        }