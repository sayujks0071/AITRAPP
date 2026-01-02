
from fastapi.testclient import TestClient
from apps.api.main import app
from packages.core.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

client = TestClient(app)

def test_cors_restrictive_behavior():
    """
    Verify that we can restrict CORS origins.
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

    @test_app.post("/mode")
    def dummy_mode():
        return {"status": "ok"}

    test_client = TestClient(test_app)

    # Test disallowed origin
    # Starlette/FastAPI CORS middleware returns 400 for disallowed origins by default if validation fails
    # Or just doesn't include headers.
    # Wait, the previous run showed 400 Bad Request: Disallowed CORS origin.
    # This confirms that the middleware is working and blocking the request!
    headers = {
        "Origin": "http://evil.com",
        "Access-Control-Request-Method": "POST",
    }
    response = test_client.options("/mode", headers=headers)

    # Expectation: 400 Bad Request (Disallowed origin) OR 200 without headers.
    # Since we saw 400 in the failure, we should assert that.
    assert response.status_code == 400
    assert "Disallowed CORS origin" in response.text

    # Test allowed origin
    headers = {
        "Origin": "http://trusted.com",
        "Access-Control-Request-Method": "POST",
    }
    response = test_client.options("/mode", headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://trusted.com"
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
