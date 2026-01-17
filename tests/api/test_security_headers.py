
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)

def test_security_headers():
    # Use /health endpoint which is known to exist
    response = client.get("/health")

    # Check HSTS
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"

    # Check X-Content-Type-Options
    assert response.headers["X-Content-Type-Options"] == "nosniff"

    # Check X-Frame-Options
    assert response.headers["X-Frame-Options"] == "DENY"

    # Check CSP
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]

    # Check Referrer-Policy
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

def test_security_headers_on_error():
    # Headers should be present even on 401/404/500
    # Accessing protected path without key -> 401
    response = client.get("/non-existent-path")
    # Don't assert 404, because Auth middleware intercepts it first returning 401
    assert response.status_code in [401, 403, 404]

    # Verify headers are present
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
