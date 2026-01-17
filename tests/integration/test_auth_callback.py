import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from apps.api.routes.kite_auth import router

class TestKiteAuthCallback:

    @pytest.fixture
    def client(self):
        """Create a clean FastAPI app with only the auth router"""
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @patch("apps.api.routes.kite_auth.KiteAuth")
    def test_callback_success(self, MockKiteAuth, client):
        # Setup mock
        mock_auth_instance = MockKiteAuth.return_value
        mock_auth_instance.exchange_request_token.return_value = "new_access_token"

        # Make request
        response = client.get("/auth/kite/callback?request_token=test_token&status=success")

        # Verify response
        assert response.status_code == 200
        assert "Authentication Successful" in response.text

        # Verify interactions
        mock_auth_instance.exchange_request_token.assert_called_once_with("test_token")
        mock_auth_instance.persist_access_token.assert_called_once_with("new_access_token")

    def test_callback_failure_status(self, client):
        # Make request with status failure
        response = client.get("/auth/kite/callback?request_token=test_token&status=failure")

        # Verify response
        assert response.status_code == 400
        assert "Auth Failed" in response.text

    def test_callback_missing_token(self, client):
        # Make request without token
        response = client.get("/auth/kite/callback?status=success")

        # Verify response
        assert response.status_code == 400
        assert "Missing request_token" in response.text

    @patch("apps.api.routes.kite_auth.KiteAuth")
    def test_callback_exception(self, MockKiteAuth, client):
        # Setup mock to raise exception
        mock_auth_instance = MockKiteAuth.return_value
        mock_auth_instance.exchange_request_token.side_effect = Exception("Exchange failed")

        # Make request
        response = client.get("/auth/kite/callback?request_token=test_token&status=success")

        # Verify response
        assert response.status_code == 500
        assert "Auth Error" in response.text
