import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


def test_cors_restrictive_behavior():
    """
    Verify that the actual app uses settings.cors_origins correctly.
    
    This test patches the settings module to use restrictive CORS origins
    and verifies that the app properly restricts access.
    """
    # Import AppMode to use the actual enum
    from packages.core.config import AppMode
    
    # Patch the settings at the apps.api.main level to ensure test isolation
    with patch("apps.api.main.settings") as mock_settings:
        # Set up mock settings with restrictive CORS
        mock_settings.cors_origins = ["http://trusted.com"]
        mock_settings.app_mode = AppMode.PAPER  # Use actual enum
        mock_settings.enable_metrics = False
        
        # Import the app - it will use our mocked settings
        # Note: This assumes the app hasn't been imported yet in this test session,
        # or that the CORS middleware is set up dynamically
        from apps.api.main import app
        
        test_client = TestClient(app, raise_server_exceptions=False)

        # Test disallowed origin
        headers = {
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "GET",
        }
        response = test_client.options("/health", headers=headers)

        # Expectation: 400 Bad Request (Disallowed origin) OR 200 without CORS headers,
        # depending on the Starlette/FastAPI version.
        if response.status_code == 400:
            # Some versions explicitly reject disallowed origins with 400.
            assert "Disallowed CORS origin" in response.text
        elif response.status_code == 200:
            # Other versions simply omit CORS headers for disallowed origins.
            assert "access-control-allow-origin" not in response.headers
        else:
            pytest.fail(
                f"Unexpected status code for disallowed origin: {response.status_code}"
            )

        # Test allowed origin
        headers = {
            "Origin": "http://trusted.com",
            "Access-Control-Request-Method": "GET",
        }
        response = test_client.options("/health", headers=headers)
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://trusted.com"

def test_default_is_permissive():
    """
    Verify the default is still permissive (to avoid breaking changes)
    unless the user changes config.
    """
    from packages.core.config import settings
    from apps.api.main import app
    
    if settings.cors_origins != ["*"]:
        pytest.skip("Default CORS origins have been overridden; permissive-default behavior is not applicable.")

    test_client = TestClient(app, raise_server_exceptions=False)
    headers = {
        "Origin": "http://evil.com",
        "Access-Control-Request-Method": "GET",
    }
    response = test_client.options("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*" or \
           response.headers.get("access-control-allow-origin") == "http://evil.com"
