from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import sys

# Ensure root is in python path
sys.path.insert(0, os.getcwd())

from apps.api.routes.kite_auth import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_kite_callback_success():
    with patch("apps.api.routes.kite_auth.KiteAuth") as MockKiteAuth:
        mock_auth = MockKiteAuth.return_value
        mock_auth.exchange_request_token.return_value = "new_access_token"

        response = client.get("/auth/kite/callback?status=success&request_token=req_123")

        assert response.status_code == 200
        assert "Authentication Successful" in response.text

        mock_auth.exchange_request_token.assert_called_with("req_123")
        mock_auth.persist_access_token.assert_called_with("new_access_token")

def test_kite_callback_failure_status():
    response = client.get("/auth/kite/callback?status=error&request_token=req_123")
    assert response.status_code == 400
    assert "Auth Failed" in response.text

def test_kite_callback_missing_token():
    response = client.get("/auth/kite/callback?status=success")
    assert response.status_code == 400
    assert "Missing request_token" in response.text

def test_kite_callback_exception():
    with patch("apps.api.routes.kite_auth.KiteAuth") as MockKiteAuth:
        mock_auth = MockKiteAuth.return_value
        mock_auth.exchange_request_token.side_effect = Exception("Exchange failed")

        response = client.get("/auth/kite/callback?status=success&request_token=req_123")

        assert response.status_code == 500
        assert "Auth Error" in response.text
