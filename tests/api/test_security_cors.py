import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
import os


def test_cors_origins_field_validator():
    """
    Test that the field_validator correctly parses CORS origins from various formats.
    """
    from packages.core.config import Settings
    
    # Test 1: JSON array string
    os.environ['CORS_ORIGINS'] = '["http://localhost:8000","http://127.0.0.1:8000"]'
    os.environ['API_SECRET_KEY'] = 'test-secret-key-for-testing-only-1234'
    settings1 = Settings()
    assert settings1.cors_origins == ["http://localhost:8000", "http://127.0.0.1:8000"]
    
    # Test 2: Single string (fallback)
    os.environ['CORS_ORIGINS'] = 'http://single-origin.com'
    settings2 = Settings()
    assert settings2.cors_origins == ["http://single-origin.com"]
    
    # Test 3: Invalid JSON object should raise ValueError
    os.environ['CORS_ORIGINS'] = '{"key": "value"}'
    with pytest.raises(ValueError, match="CORS_ORIGINS must be a JSON array"):
        Settings()
    
    # Test 4: JSON array with non-string values should raise ValueError
    os.environ['CORS_ORIGINS'] = '[1, 2, 3]'
    with pytest.raises(ValueError, match="CORS_ORIGINS must contain only string values"):
        Settings()
    
    # Cleanup
    os.environ.pop('CORS_ORIGINS', None)


def test_cors_restrictive_behavior():
    """
    Verify that CORS middleware can restrict origins correctly.
    
    This test creates a minimal FastAPI app with CORS middleware configured
    to verify that the middleware behaves as expected with restrictive origins.
    """
    # Create a test app with restrictive CORS middleware
    test_app = FastAPI()
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://trusted.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @test_app.get("/health")
    def health():
        return {"status": "ok"}

    test_client = TestClient(test_app, raise_server_exceptions=False)

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
        # We need to import pytest here or at the top of the file
        import pytest
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
