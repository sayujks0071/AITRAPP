import os
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.core.config import settings

client = TestClient(app)

# Use the secret key from env or default
API_KEY = settings.api_secret_key

def test_health_check_public():
    """Test that health check is public"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_metrics_public():
    """Test that metrics endpoint is public"""
    response = client.get("/metrics")
    # It might return 200 or 500 depending on prometheus setup in test env
    # but it should NOT return 401
    assert response.status_code != 401

def test_protected_endpoint_without_key():
    """Test accessing protected endpoint without key fails"""
    response = client.get("/positions")
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API Key"}

def test_protected_endpoint_with_invalid_key():
    """Test accessing protected endpoint with invalid key fails"""
    response = client.get("/positions", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401

def test_protected_endpoint_with_valid_key_header():
    """Test accessing protected endpoint with valid key in header works"""
    # Note: We expect 200 or some other success code (or even 500 if internal logic fails)
    # but NOT 401.
    # Since /positions requires orchestrator which might not be init in test,
    # we just check we pass auth layer.
    response = client.get("/positions", headers={"X-API-Key": API_KEY})
    assert response.status_code != 401

def test_protected_endpoint_with_valid_key_query():
    """Test accessing protected endpoint with valid key in query param works"""
    response = client.get(f"/positions?api_key={API_KEY}")
    assert response.status_code != 401

def test_cors_options_bypass_auth():
    """Test that OPTIONS requests bypass auth (for CORS)"""
    response = client.options("/positions")
    # Should not be 401 (Auth error)
    # It might be 405 (Method Not Allowed) or 200 depending on app setup
    assert response.status_code != 401
