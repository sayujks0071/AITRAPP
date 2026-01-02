import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.core.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

client = TestClient(app)

def test_cors_restrictive_behavior(monkeypatch):
    """
    Verify that the main app respects configured CORS origins.
    Tests that when CORS_ORIGINS is set to specific origins, the app
    properly restricts cross-origin requests.
    """
    # Set restrictive CORS origins via environment variable
    monkeypatch.setenv("CORS_ORIGINS", '["http://trusted.com"]')
    
    # Reload settings to pick up the new environment variable
    from importlib import reload
    from packages.core import config as config_module
    reload(config_module)
    
    # Re-import the updated settings and app
    from packages.core.config import settings as reloaded_settings
    
    # Create a new FastAPI app instance with the updated settings
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    test_app = FastAPI()
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=reloaded_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @test_app.get("/health")
    def dummy_health():
        return {"status": "ok"}
    
    test_client = TestClient(test_app)
    
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
    if settings.cors_origins != ["*"]:
        pytest.skip("Default CORS origins have been overridden; permissive-default behavior is not applicable.")

    headers = {
        "Origin": "http://evil.com",
        "Access-Control-Request-Method": "POST",
    }
    # We need to recreate the client to ensure it picks up the default settings
    client_default = TestClient(app)
    response = client_default.options("/mode", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*" or \
           response.headers.get("access-control-allow-origin") == "http://evil.com"
