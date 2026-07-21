"""
Pytest configuration and fixtures for Nexus AI tests.
Provides reusable fixtures for database, API client, and authentication.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.database import get_db
from app.main import app
from app.models import Tenant, User, ClientWorkspace
from app.auth.security import hash_password, create_access_token

# Test database URL (in-memory SQLite for fast tests)
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=test_engine)

    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as tc:
        yield tc

    app.dependency_overrides.clear()


@pytest.fixture
def test_tenant(db_session):
    """Create a test tenant."""
    tenant = Tenant(
        id="test-tenant-1",
        company_name="Test Corp",
        tenant_type="saas_subscriber",
        is_active=True,
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant


@pytest.fixture
def test_user(db_session, test_tenant):
    """Create a test user."""
    user = User(
        id="test-user-1",
        tenant_id=test_tenant.id,
        email="test@example.com",
        name="Test User",
        hashed_password=hash_password("testpass123"),
        is_global_admin=False,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_admin_user(db_session, test_tenant):
    """Create a test admin user."""
    user = User(
        id="test-admin-1",
        tenant_id=test_tenant.id,
        email="admin@example.com",
        name="Admin User",
        hashed_password=hash_password("adminpass123"),
        is_global_admin=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_workspace(db_session, test_tenant):
    """Create a test workspace."""
    workspace = ClientWorkspace(
        id="test-workspace-1",
        tenant_id=test_tenant.id,
        brand_name="Test Brand",
        autopilot_enabled=False,
        monthly_budget_cap=500000,
    )
    db_session.add(workspace)
    db_session.commit()
    return workspace


@pytest.fixture
def auth_headers(test_user):
    """Get authentication headers for test user."""
    token = create_access_token(
        user_id=test_user.id,
        tenant_id=test_user.tenant_id,
        role="client"
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(test_admin_user):
    """Get authentication headers for admin user."""
    token = create_access_token(
        user_id=test_admin_user.id,
        tenant_id=test_admin_user.tenant_id,
        role="admin",
        is_admin=True
    )
    return {"Authorization": f"Bearer {token}"}
