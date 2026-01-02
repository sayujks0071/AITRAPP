import pytest
from fastapi.testclient import TestClient
from packages.core.config import settings

# Note: We don't directly import the app here to avoid initialization issues
# Instead, we'll test the settings configuration

def test_cors_origins_configuration():
    """
    Verify that CORS origins can be configured via settings.
    This test validates that the settings.cors_origins is properly configured
    and will be used by the main app's CORSMiddleware.
    """
    # Test that cors_origins is configurable and accessible
    assert hasattr(settings, 'cors_origins')
    assert isinstance(settings.cors_origins, list)
    
    # Verify default or configured value is present
    assert len(settings.cors_origins) > 0
    
    # Each origin should be a string
    for origin in settings.cors_origins:
        assert isinstance(origin, str)


def test_cors_origins_used_by_app():
    """
    Verify that the main app actually uses settings.cors_origins.
    This test checks that the app's CORS middleware is configured
    with the origins from settings.
    """
    from apps.api.main import app
    from fastapi.middleware.cors import CORSMiddleware
    
    # Find the CORS middleware in the app's middleware stack
    cors_middleware = None
    for middleware in app.user_middleware:
        # Check if this is the CORSMiddleware using type comparison
        if middleware.cls is CORSMiddleware or middleware.cls.__name__ == "CORSMiddleware":
            cors_middleware = middleware
            break
    
    assert cors_middleware is not None, "CORSMiddleware not found in app"
    
    # Verify that the middleware options include allow_origins
    # The middleware stores options in the 'options' attribute
    assert 'allow_origins' in cors_middleware.options
    
    # Verify that the origins match settings.cors_origins
    # Note: The middleware may store origins differently, so we check if it's set
    middleware_origins = cors_middleware.options['allow_origins']
    
    # If settings has specific origins (not wildcard), verify they're configured
    if settings.cors_origins != ["*"]:
        assert middleware_origins == settings.cors_origins, \
            f"Middleware origins {middleware_origins} don't match settings {settings.cors_origins}"
    else:
        # If using wildcard, verify it's configured
        assert middleware_origins == ["*"] or "*" in middleware_origins


def test_default_cors_is_permissive():
    """
    Verify the default CORS configuration is permissive (backward compatibility).
    Only runs this test if the default wildcard setting is in use.
    """
    if settings.cors_origins != ["*"]:
        pytest.skip("Default CORS origins have been overridden; permissive-default behavior is not applicable.")
    
    # Import app after confirming we're testing default behavior
    from apps.api.main import app
    
    # Create a test client for the actual app
    client = TestClient(app)
    
    # Test that the wildcard origin allows any origin
    headers = {
        "Origin": "http://example.com",
        "Access-Control-Request-Method": "POST",
    }
    response = client.options("/health", headers=headers)
    
    # With wildcard (*), the response should either:
    # - Return status 200 with access-control-allow-origin: *
    # - Or return status 200 with the requested origin echoed back
    assert response.status_code == 200
    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin in ["*", "http://example.com"], \
        f"Expected wildcard or echo origin, got {allow_origin}"

