"""
Database seeding script for Nexus AI.
Creates initial admin user, default tenant, and sample data.
"""
import asyncio
import uuid
import random
from datetime import datetime, timedelta
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker, engine, Base
from app.models import (
    Tenant, User, ClientWorkspace, SecureIntegration,
    AgentActionLog, ApprovalQueue, Campaign, CampaignMetric,
    PlanConfig
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed_database():
    """Seed the database with initial data."""
    print("[SEED] Starting database seeding...")
    
    # Create tables (clean drop and recreate)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("[SUCCESS] Tables dropped and recreated")
    
    async with async_session_maker() as db:
        # Check if already seeded
        from sqlalchemy import select, func
        
        # Seed default plan configurations first
        plan_count = await db.execute(select(func.count(PlanConfig.id)))
        if plan_count.scalar() == 0:
            default_plans = [
                PlanConfig(
                    id="starter", name="Starter", price="₦0", period="forever",
                    max_workspaces=1, max_agents=5, ad_budget_cap=500000,
                    has_basic_analytics=True, has_advanced_analytics=False,
                    has_priority_support=False, has_team_members=False,
                    has_white_label_reports=False, has_dedicated_manager=False,
                    can_access_ab_testing=False, can_access_audit_log=False,
                    can_access_content_studio=True, can_access_integrations=True,
                    can_access_team=False
                ),
                PlanConfig(
                    id="professional", name="Pro", price="₦99K", period="month",
                    max_workspaces=-1, max_agents=5, ad_budget_cap=1000000,
                    has_basic_analytics=True, has_advanced_analytics=True,
                    has_priority_support=True, has_team_members=False,
                    has_white_label_reports=False, has_dedicated_manager=False,
                    can_access_ab_testing=True, can_access_audit_log=True,
                    can_access_content_studio=True, can_access_integrations=True,
                    can_access_team=False
                ),
                PlanConfig(
                    id="agency", name="Business", price="₦299K", period="month",
                    max_workspaces=-1, max_agents=5, ad_budget_cap=-1,
                    has_basic_analytics=True, has_advanced_analytics=True,
                    has_priority_support=True, has_team_members=True,
                    has_white_label_reports=True, has_dedicated_manager=True,
                    can_access_ab_testing=True, can_access_audit_log=True,
                    can_access_content_studio=True, can_access_integrations=True,
                    can_access_team=True
                )
            ]
            for p in default_plans:
                db.add(p)
            await db.flush()
            print("[SUCCESS] Seeded default plan configurations")

        tenant_count = await db.execute(select(func.count(Tenant.id)))
        if tenant_count.scalar() > 0:
            print("[WARNING] Database already has data. Skipping seed.")
            return
        
        # Create admin tenant
        admin_tenant_id = str(uuid.uuid4())
        admin_tenant = Tenant(
            id=admin_tenant_id,
            company_name="Platform Admin",
            tenant_type="agency",
            is_active=True,
        )
        db.add(admin_tenant)
        await db.flush()
        print(f"[SUCCESS] Created admin tenant: {admin_tenant_id}")
        
        # Create admin user
        admin_user_id = str(uuid.uuid4())
        admin_user = User(
            id=admin_user_id,
            tenant_id=admin_tenant_id,
            email="admin@platform.com",
            name="Alex Chen",
            hashed_password=pwd_context.hash("admin123"),
            is_global_admin=True,
        )
        db.add(admin_user)
        await db.flush()
        print("[SUCCESS] Created admin user: admin@platform.com / admin123")
        
        # Create three distinct client accounts representing Starter, Pro, and Business plans
        workspaces_to_seed = [
            {
                "tenant_name": "Starter Co",
                "email": "starter@nexus.ai",
                "user_name": "David Miller",
                "ws_id": "ws-starter-01",
                "brand_name": "Starter Co",
                "budget_cap": 500000, # ₦500K
                "platforms": ["google"],
                "billing_plan": "starter"
            },
            {
                "tenant_name": "Acme Corp",
                "email": "sarah@acmecorp.com",
                "user_name": "Sarah Anderson",
                "ws_id": "ws-acme-01",
                "brand_name": "Acme Corp",
                "budget_cap": 1000000, # ₦1M
                "platforms": ["meta", "google"],
                "billing_plan": "professional"
            },
            {
                "tenant_name": "Business Corp",
                "email": "business@nexus.ai",
                "user_name": "Mark Jackson",
                "ws_id": "ws-business-01",
                "brand_name": "Business Corp",
                "budget_cap": 0, # Unlimited
                "platforms": ["meta", "google", "tiktok"],
                "billing_plan": "agency"
            }
        ]

        for ws_info in workspaces_to_seed:
            # Create Tenant
            client_tenant_id = str(uuid.uuid4())
            client_tenant = Tenant(
                id=client_tenant_id,
                company_name=ws_info["tenant_name"],
                tenant_type="saas_subscriber",
                billing_plan=ws_info["billing_plan"],
                is_active=True,
            )
            db.add(client_tenant)
            await db.flush()
            print(f"[SUCCESS] Created tenant for {ws_info['email']}: {client_tenant_id}")

            # Create User
            client_user_id = str(uuid.uuid4())
            client_user = User(
                id=client_user_id,
                tenant_id=client_tenant_id,
                email=ws_info["email"],
                name=ws_info["user_name"],
                hashed_password=pwd_context.hash("password123"),
                is_global_admin=False,
            )
            db.add(client_user)
            await db.flush()
            print(f"[SUCCESS] Created user: {ws_info['email']} / password123")

            # Create Workspace
            workspace_id = ws_info["ws_id"]
            workspace = ClientWorkspace(
                id=workspace_id,
                tenant_id=client_tenant_id,
                brand_name=ws_info["brand_name"],
                brand_voice_profile="Professional, friendly, and authentic. Focus on value and community.",
                autopilot_enabled=False,
                monthly_budget_cap=ws_info["budget_cap"],
                roas_threshold=2.0,
                is_active=True,
            )
            db.add(workspace)
            await db.flush()
            print(f"[SUCCESS] Created workspace: {workspace_id}")

            # Pure, clean workspace initialization - no mock integrations, logs, or approvals seeded.
            print(f"[SUCCESS] Clean workspace initialized: {workspace_id}")

        
        # Commit all changes
        await db.commit()
        print("\n[SUCCESS] Database seeding completed successfully!")
        print("\n[INFO] Login credentials:")
        print("   Admin: admin@platform.com / admin123")
        print("   Client: sarah@acmecorp.com / password123")


if __name__ == "__main__":
    asyncio.run(seed_database())