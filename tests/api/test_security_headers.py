from fastapi.testclient import TestClient

from apps.api.main import app
from packages.core.config import settings

client = TestClient(app)


def test_security_headers_present():
    """Test that security headers are present on successful responses"""
    response = client.get("/health")
    assert response.status_code == 200

    headers = response.headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "1; mode=block" in headers["X-XSS-Protection"]
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    # Headers are case-insensitive in requests/starlette, but dictionary keys might be lower-cased or not depending on client.
    # TestClient usually lowercases them? Let's check keys ignoring case.
    keys = {k.lower(): v for k, v in headers.items()}

    assert "strict-transport-security" in keys
    assert "content-security-policy" in keys

    # Check CSP content
    csp = keys["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net" in csp


def test_security_headers_on_error():
    """Test that security headers are present on error responses (404)"""
    # We need to authenticate to reach the 404 handler
    headers = {"X-API-Key": settings.api_secret_key}
    response = client.get("/nonexistent-endpoint", headers=headers)
    assert response.status_code == 404

    headers = response.headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"


def test_security_headers_on_auth_fail():
    """Test that security headers are present on auth failure (403/401)"""
    # Request a private endpoint without API key
    response = client.get("/orders")
    # APIKeyMiddleware returns 401 JSONResponse
    assert response.status_code == 401

    headers = response.headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
