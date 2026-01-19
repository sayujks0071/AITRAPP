import pytest
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)

def test_security_headers_presence():
    """Test that security headers are present in responses"""
    response = client.get("/health")
    assert response.status_code == 200

    headers = response.headers

    # Check for Security Headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert headers.get("Strict-Transport-Security") == "max-age=63072000; includeSubDomains"
    assert "Content-Security-Policy" in headers
    assert headers.get("Referrer-Policy") == "no-referrer"

def test_csp_content():
    """Test Content-Security-Policy header content"""
    response = client.get("/health")
    csp = response.headers.get("Content-Security-Policy", "")

    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp or "frame-ancestors 'self'" in csp # or implicit via X-Frame-Options

def test_security_headers_on_error():
    """Test that security headers are present even on 403 Forbidden responses"""
    # Request a protected endpoint without credentials
    response = client.get("/positions")
    assert response.status_code == 401

    headers = response.headers
    assert headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in headers
