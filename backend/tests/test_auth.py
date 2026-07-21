"""
Tests for authentication endpoints.
Tests login, registration, token validation, and password hashing.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestRegistration:
    """Tests for user registration endpoint."""
    
    def test_register_success(self, client, db_session):
        """Test successful user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "name": "New User",
                "company_name": "New Corp",
                "tenant_type": "saas_subscriber"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["name"] == "New User"
    
    def test_register_duplicate_email(self, client, test_user):
        """Test registration with existing email."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "SecurePass123!",
                "name": "Duplicate User",
                "company_name": "Duplicate Corp"
            }
        )
        
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "SecurePass123!",
                "name": "Test User",
                "company_name": "Test Corp"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_register_short_password(self, client):
        """Test registration with short password."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "short",
                "name": "Test User",
                "company_name": "Test Corp"
            }
        )
        
        assert response.status_code == 422


class TestLogin:
    """Tests for user login endpoint."""
    
    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpass123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == test_user.email
    
    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "invalid credentials" in response.json()["detail"].lower()
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "testpass123"
            }
        )
        
        assert response.status_code == 401
    
    def test_login_inactive_tenant(self, client, test_user, test_tenant, db_session):
        """Test login with inactive tenant."""
        test_tenant.is_active = False
        db_session.commit()
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpass123"
            }
        )
        
        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"].lower()


class TestGetMe:
    """Tests for get current user endpoint."""
    
    def test_get_me_success(self, client, auth_headers):
        """Test getting current user info."""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "tenant" in data
    
    def test_get_me_unauthorized(self, client):
        """Test getting current user without token."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    def test_get_me_invalid_token(self, client):
        """Test getting current user with invalid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401


class TestPasswordHashing:
    """Tests for password hashing utilities."""
    
    def test_hash_password(self):
        """Test password hashing."""
        from app.auth.security import hash_password, verify_password
        
        password = "testpass123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrongpassword", hashed)
    
    def test_different_hashes(self):
        """Test that same password produces different hashes."""
        from app.auth.security import hash_password, verify_password
        
        password = "testpass123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2  # Different salts
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestTokenCreation:
    """Tests for JWT token creation and validation."""
    
    def test_create_access_token(self):
        """Test creating access token."""
        from app.auth.security import create_access_token, decode_access_token
        from app.config import settings
        
        token = create_access_token(
            user_id="user-123",
            tenant_id="tenant-456",
            role="client"
        )
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and verify
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["tenant_id"] == "tenant-456"
        assert payload["role"] == "client"
    
    def test_expired_token(self):
        """Test expired token raises error."""
        from app.auth.security import create_access_token, decode_access_token
        from datetime import datetime, timedelta
        import jwt
        
        # Create token that expires immediately
        payload = {
            "sub": "user-123",
            "tenant_id": "tenant-456",
            "exp": datetime.utcnow() - timedelta(hours=1),
            "iat": datetime.utcnow() - timedelta(hours=2)
        }
        
        from app.config import settings
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_access_token(token)