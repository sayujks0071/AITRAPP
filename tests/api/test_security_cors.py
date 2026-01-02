
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.core.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

client = TestClient(app)

def test_cors_restrictive_behavior():
    """
    Verify that the main app's CORS middleware is configured to use settings.cors_origins.
    
    This test verifies that the actual app in apps.api.main uses settings.cors_origins
    by inspecting the middleware configuration.
    """
    # Verify that the app has CORSMiddleware configured
    cors_middleware = None
    for middleware in app.user_middleware:
        if middleware.cls.__name__ == "CORSMiddleware":
            cors_middleware = middleware
            break
    
    assert cors_middleware is not None, "CORSMiddleware not found in app configuration"
    
    # Verify that the middleware uses settings.cors_origins
    # The middleware options are stored in the middleware.kwargs dict
    middleware_origins = cors_middleware.kwargs.get("allow_origins", [])
    
    # Check that middleware is configured to use settings.cors_origins
    # Since the app is created at module level, we verify it uses the same origins
    assert middleware_origins == settings.cors_origins, \
        f"CORS middleware origins {middleware_origins} don't match settings.cors_origins {settings.cors_origins}"


def test_default_is_permissive():
    """
    Verify the default CORS configuration is permissive (allows all origins).
    Tests the actual app's CORS behavior with the default settings.
    """
    if settings.cors_origins != ["*"]:
        pytest.skip("Default CORS origins have been overridden; permissive-default behavior is not applicable.")
    
    # Test with the actual app client
    headers = {
        "Origin": "http://evil.com",
        "Access-Control-Request-Method": "POST",
    }
    response = client.options("/mode", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*" or \
           response.headers.get("access-control-allow-origin") == "http://evil.com"
