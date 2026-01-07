from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
from apps.api.main import app

client = TestClient(app)

def test_kite_callback_success():
    with patch("apps.api.routes.kite_auth.KiteAuth") as MockKiteAuth:
        mock_auth_instance = MockKiteAuth.return_value
        # Mock exchange to return a token
        mock_auth_instance.exchange_request_token.return_value = "new_access_token_123"
        # Mock persist to do nothing
        mock_auth_instance.persist_access_token.return_value = None

        response = client.get("/auth/kite/callback?request_token=req_token_xyz&status=success")

        assert response.status_code == 200
        assert "Authentication Successful" in response.text

        # Verify calls
        mock_auth_instance.exchange_request_token.assert_called_with("req_token_xyz")
        mock_auth_instance.persist_access_token.assert_called_with("new_access_token_123")

def test_kite_callback_failure_status():
    response = client.get("/auth/kite/callback?request_token=req_token_xyz&status=failure")
    assert response.status_code == 400
    assert "Auth Failed" in response.text

def test_kite_callback_missing_token():
    response = client.get("/auth/kite/callback?status=success")
    assert response.status_code == 400
    assert "Missing request_token" in response.text

def test_kite_callback_exchange_exception():
    with patch("apps.api.routes.kite_auth.KiteAuth") as MockKiteAuth:
        mock_auth_instance = MockKiteAuth.return_value
        mock_auth_instance.exchange_request_token.side_effect = Exception("Exchange Failed")

        response = client.get("/auth/kite/callback?request_token=req_token_xyz&status=success")

        assert response.status_code == 500
        assert "Exchange Failed" in response.text
