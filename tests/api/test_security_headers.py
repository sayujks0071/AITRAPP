import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.core.config import settings

client = TestClient(app)

def test_security_headers_present():
    """Test that security headers are present in responses"""
    response = client.get("/health")
    assert response.status_code == 200

    headers = response.headers

    # HSTS
    assert headers["Strict-Transport-Security"] == "max-age=63072000; includeSubDomains; preload"

    # X-Content-Type-Options
    assert headers["X-Content-Type-Options"] == "nosniff"

    # X-Frame-Options
    assert headers["X-Frame-Options"] == "DENY"

    # X-XSS-Protection
    assert headers["X-XSS-Protection"] == "1; mode=block"

    # Referrer-Policy
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    # CSP
    assert "Content-Security-Policy" in headers
    csp = headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    # Check for Swagger UI requirements
    assert "script-src 'self' 'unsafe-inline' 'unsafe-eval'" in csp or "script-src" in csp # rough check
    assert "object-src 'none'" in csp

    # Permissions Policy
    assert "Permissions-Policy" in headers
    assert "camera=()" in headers["Permissions-Policy"]

def test_security_headers_on_error():
    """Test that security headers are present even on 401/403 errors"""
    # 401 Missing Key
    response = client.get("/positions")
    assert response.status_code == 401
    assert "Strict-Transport-Security" in response.headers
    assert "Content-Security-Policy" in response.headers

    # 403 Invalid Key
    headers = {"X-API-Key": "invalid"}
    response = client.get("/positions", headers=headers)
    assert response.status_code == 403
    assert "Strict-Transport-Security" in response.headers
    assert "Content-Security-Policy" in response.headers
