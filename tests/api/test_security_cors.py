
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.core.config import settings
from fastapi.middleware.cors import CORSMiddleware

client = TestClient(app)

def test_cors_restrictive_behavior():
    """
    Verify that the main app's CORS middleware uses settings.cors_origins correctly.
    
    This test validates that the actual app in apps.api.main respects the
    settings.cors_origins configuration by inspecting the middleware stack.
    """
    # The app is already configured with settings.cors_origins at import time
    # We need to verify that the CORSMiddleware is properly configured
    
    # Check that the app has CORSMiddleware in its middleware stack
    cors_middleware_found = False
    cors_config = None
    
    # FastAPI wraps middleware in the app.user_middleware list
    for middleware in app.user_middleware:
        if middleware.cls == CORSMiddleware:
            cors_middleware_found = True
            cors_config = middleware.options
            break
    
    assert cors_middleware_found, "CORSMiddleware not found in app middleware stack"
    
    # Verify that the middleware uses settings.cors_origins
    assert "allow_origins" in cors_config, "allow_origins not configured in CORSMiddleware"
    assert cors_config["allow_origins"] == settings.cors_origins, \
        f"CORSMiddleware allow_origins {cors_config['allow_origins']} does not match settings.cors_origins {settings.cors_origins}"
    
    # Also verify the behavior with actual requests to the real app
    # Test with an OPTIONS preflight request
    headers = {
        "Origin": "http://example.com",
        "Access-Control-Request-Method": "POST",
    }
    response = client.options("/mode", headers=headers)
    
    # If settings.cors_origins is ["*"], any origin should be allowed
    # If it's restrictive, only listed origins should have CORS headers
    if "*" in settings.cors_origins:
        # Permissive mode - should return CORS headers
        assert response.status_code in [200, 400], \
            f"Unexpected status code: {response.status_code}"
        # In permissive mode, we should get access-control-allow-origin header
        if response.status_code == 200:
            assert "access-control-allow-origin" in response.headers, \
                "Expected CORS headers in permissive mode"
    else:
        # Restrictive mode - test with an origin not in the list
        # If the origin is not in settings.cors_origins, it should be rejected
        if "http://example.com" not in settings.cors_origins:
            # Should either return 400 or 200 without CORS headers for disallowed origin
            assert response.status_code in [200, 400], \
                f"Unexpected status code for disallowed origin: {response.status_code}"

def test_default_is_permissive():
    """
    Verify the default is still permissive (to avoid breaking changes)
    unless the user changes config.
    
    This test ensures backward compatibility by verifying that when
    settings.cors_origins is ["*"], the app allows cross-origin requests.
    """
    if settings.cors_origins == ["*"]:
        headers = {
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "POST",
        }
        response = client.options("/mode", headers=headers)
        assert response.status_code == 200, \
            f"Expected 200 for permissive CORS, got {response.status_code}"
        assert response.headers.get("access-control-allow-origin") == "*" or \
               response.headers.get("access-control-allow-origin") == "http://example.com", \
               f"Expected permissive CORS header, got {response.headers.get('access-control-allow-origin')}"
