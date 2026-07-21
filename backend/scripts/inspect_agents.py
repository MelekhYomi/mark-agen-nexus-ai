"""
Nexus AI — 13-Agent Society Swarm Standalone Inspector & Trial Run Script
Triggers each of the 13 agents sequentially, logs their inner thinking/reasoning chain,
and outputs high-fidelity JSON results to detail the entire collaborative growth cycle.
"""
import asyncio
import os
import sys
import json
from datetime import datetime

# Add the parent directory to Python path so we can import app modules properly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
from app.models import Base, Tenant, ClientWorkspace, TenantType, ApprovalStatus
from app.agents.orchestrator import AgentOrchestrator

async def run_inspection():
    print("=" * 100)
    print("NEXUS AI (MARK AGEN) - 13-AGENT SOCIETY SWARM ACTIVE INSPECTION RUN")
    print("=" * 100)
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Target Database: {settings.DATABASE_URL}")
    print("-" * 100)

    # Initialize Engine & Session Local
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        print("[Step 1] Initializing Database Schema...")
        await conn.run_sync(Base.metadata.create_all)
        print("[Step 1] Schema verified and loaded successfully.")

    async with SessionLocal() as db:
        # Seed test workspace
        print("\n[Step 2] Setting up Test Tenant & Brand Workspace...")
        tenant_id = "t_inspection_test"
        workspace_id = "ws_inspection_test"

        from sqlalchemy import select
        # 1. Tenant
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        res = await db.execute(stmt)
        tenant = res.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(
                id=tenant_id,
                company_name="Inspection Tech Corp",
                tenant_type=TenantType.SAAS_SUBSCRIBER,
                is_active=True
            )
            db.add(tenant)
            await db.flush()

        # 2. Workspace
        stmt = select(ClientWorkspace).where(ClientWorkspace.id == workspace_id)
        res = await db.execute(stmt)
        workspace = res.scalar_one_or_none()
        if not workspace:
            workspace = ClientWorkspace(
                id=workspace_id,
                tenant_id=tenant_id,
                brand_name="Nexus Inspect",
                brand_voice_profile="Highly professional, strategic B2B tech voice, focused on ROI and system safety.",
                autopilot_enabled=False, # Co-pilot mode for human approvals
                monthly_budget_cap=500000, # $5,000 in cents
                roas_threshold=2.5,
                is_active=True
            )
            db.add(workspace)
            await db.commit()
            print(f"[Step 2] Created fresh workspace: '{workspace.brand_name}'")
        else:
            print(f"[Step 2] Reusing existing workspace: '{workspace.brand_name}'")

        # 3. Instantiate Orchestrator
        print("\n[Step 3] Initializing Agent Orchestrator with 13-Agent Swarm...")
        orchestrator = AgentOrchestrator(db, workspace_id)
        print("[Step 3] Swarm instantiated successfully.")

        # Let's run individual agents sequentially and document results
        print("\n" + "=" * 100)
        print("EXECUTING ALL 13 AUTONOMOUS AGENTS - SEQUENTIAL COGNITIVE AUDIT")
        print("=" * 100)

        # Agent 1: Analytics
        print("\n--- [AGENT 1/13] Analytics Expert ---")
        analytics_res = await orchestrator.analytics.analyze_performance()
        print(f"Thinking:\n{analytics_res.get('thinking', 'N/A')}\n")
        print(f"Output:\n{json.dumps(analytics_res, indent=2)}")

        # Agent 2: Social Media Manager
        print("\n--- [AGENT 2/13] Social Media Manager ---")
        social_res = await orchestrator.social_manager.generate_content_suggestions()
        print(f"Thinking:\n{social_res.get('thinking', 'N/A')}\n")
        print(f"Output Suggestions Count: {len(social_res.get('suggestions', []))}")
        print(f"Output:\n{json.dumps(social_res, indent=2)[:800]}... [Truncated]")

        # Agent 3: Digital Marketer
        print("\n--- [AGENT 3/13] Digital Marketer ---")
        marketer_res = await orchestrator.digital_marketer.develop_strategy()
        print(f"Thinking:\n{marketer_res.get('thinking', 'N/A')}\n")
        print(f"Output:\n{json.dumps(marketer_res, indent=2)}")

        # Agent 4: Ads Manager
        print("\n--- [AGENT 4/13] Ads Manager ---")
        ads_res = await orchestrator.ads_manager.optimize_campaigns()
        print(f"Thinking:\n{ads_res.get('thinking', 'N/A')}\n")
        print(f"Output:\n{json.dumps(ads_res, indent=2)}")

        # Agent 5: SEO Expert
        print("\n--- [AGENT 5/13] SEO Expert ---")
        seo_res = await orchestrator.seo_expert.improve_rankings()
        print(f"Thinking:\n{seo_res.get('thinking', 'N/A')}\n")
        print(f"Output:\n{json.dumps(seo_res, indent=2)}")

        # Agent 6: Brand Guardian
        print("\n--- [AGENT 6/13] Brand & Compliance Guardian ---")
        brand_res = await orchestrator.brand_guardian.audit_content(
            content="Scale your startup with Qwen AI agents on Nexus AI! High-performance marketing pipelines on autopilot.",
            platform="linkedin"
        )
        print(f"Thinking:\n{brand_res.get('thinking', 'N/A')}\n")
        print(f"Output:\n{json.dumps(brand_res, indent=2)}")

        # Agent 7: Conversion Rate Optimizer (CRO)
        print("\n--- [AGENT 7/13] Conversion & A/B Optimizer ---")
        campaigns_input = [
            {"campaign_id": "c1", "campaign_name": "Nexus Launch", "ctr": 0.015, "cpc": 1.20, "cpa": 45.0, "spend": 1000.0, "conversions": 22}
        ]
        conversion_res = await orchestrator.conversion_optimizer.optimize_conversion_funnels(campaigns_input)
        print(f"Thinking:\n{conversion_res.get('thinking', 'N/A')}\n")
        print(f"Output:\n{json.dumps(conversion_res, indent=2)}")

        # Agent 8: Community Engagement
        print("\n--- [AGENT 8/13] Community Engagement & Sentiment ---")
        comments_input = [
            {"id": "c_001", "author": "Alice", "text": "This multi-agent coordination is incredible! Does it support Twitter publishing?", "platform": "linkedin"}
        ]
        community_res = await orchestrator.community_engagement.process_engagement_stream(comments_input)
        print(f"Thinking:\n{community_res.get('thinking', 'N/A')}\n")
        print(f"Output:\n{json.dumps(community_res, indent=2)}")

        # Agent 9: Market Intelligence
        print("\n--- [AGENT 9/13] Market Intelligence & Scraping ---")
        market_res = await orchestrator.market_intelligence.generate_competitor_brief("B2B SaaS Growth Marketing")
        print(f"Thinking:\n{market_res.get('thinking', 'N/A')}\n")
        print(f"Output:\n{json.dumps(market_res, indent=2)}")

        # Agent 10: Dynamic CFO
        print("\n--- [AGENT 10/13] Dynamic CFO & Subscription ---")
        billing_history = {"subscription_status": "active", "current_tier": "PRO", "monthly_price": 79.0}
        active_usage = {"api_calls_this_month": 15000, "agents_deployed": 13}
        cfo_res = await orchestrator.dynamic_cfo.analyze_subscription_health(billing_history, active_usage)
        print(f"Thinking:\n{cfo_res.get('thinking', 'N/A')}\n")
        print(f"Output:\n{json.dumps(cfo_res, indent=2)}")

        # Agent 11: Security SRE
        print("\n--- [AGENT 11/13] SRE & Security Audit ---")
        logs_input = [
            {"timestamp": datetime.utcnow().isoformat(), "source_ip": "192.168.1.1", "request_path": "/api/v1/auth/login", "method": "POST", "status_code": 200, "payload": "{}"}
        ]
        security_res = await orchestrator.security_sre.audit_system_security(logs_input)
        print(f"Thinking:\n{security_res.get('thinking', 'N/A')}\n")
        print(f"Output:\n{json.dumps(security_res, indent=2)}")

        # Agent 12: Content Calendar Planner
        print("\n--- [AGENT 12/13] Content Calendar & Scheduler ---")
        calendar_res = await orchestrator.calendar_planner.plan_content_calendar(
            niche_strategy="High-yield B2B Lead Gen for tech SaaS using Qwen LLMs and custom images.",
            days=3
        )
        print(f"Thinking:\n{calendar_res.get('thinking', 'N/A')}\n")
        print(f"Output Saved Items Count: {calendar_res.get('calendar_items_count', 0)}")
        print(f"Output:\n{json.dumps(calendar_res, indent=2)}")

        # Agent 13: Media Generator
        print("\n--- [AGENT 13/13] Multimedia & Visual Asset Generator ---")
        media_res = await orchestrator.media_generator.generate_multimodal_assets(
            title="Accelerate startup growth with Qwen AI agents",
            media_type="IMAGE",
            platform="linkedin"
        )
        print(f"Thinking:\n{media_res.get('thinking', 'N/A')}\n")
        print(f"Output:\n{json.dumps(media_res, indent=2)}")

        print("\n" + "=" * 100)
        print("SEQUENTIAL TRIAL RUN COMPLETED SUCCESSFULLY!")
        print("=" * 100)

if __name__ == "__main__":
    asyncio.run(run_inspection())
