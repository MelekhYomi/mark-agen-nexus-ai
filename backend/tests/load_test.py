"""
Load testing script using Locust.
Tests API performance under load.
"""
from locust import HttpUser, task, between
import json


class APIUser(HttpUser):
    """Simulated API user for load testing."""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login before running tests."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass123"
            }
        )
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}
    
    @task(3)
    def get_workspaces(self):
        """Test getting workspaces."""
        if self.token:
            self.client.get(
                "/api/v1/dashboard/workspaces",
                headers=self.headers
            )
    
    @task(2)
    def get_agent_logs(self):
        """Test getting agent logs."""
        if self.token:
            self.client.get(
                "/api/v1/dashboard/agent-logs?workspace_id=ws-123&limit=50",
                headers=self.headers
            )
    
    @task(1)
    def get_approvals(self):
        """Test getting approvals."""
        if self.token:
            self.client.get(
                "/api/v1/dashboard/approvals?workspace_id=ws-123",
                headers=self.headers
            )
    
    @task(1)
    def health_check(self):
        """Test health check endpoint."""
        self.client.get("/health")