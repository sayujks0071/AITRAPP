import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from apps.api.main import app
from src.auth.kite_auth import KiteAuth

class TestAuthCallbackIntegration(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    @patch.dict(os.environ, {
        "KITE_API_KEY": "test_key",
        "KITE_API_SECRET": "test_secret",
        "APP_MODE": "PAPER"
    })
    @patch("src.auth.kite_auth.KiteConnect")
    @patch("src.auth.kite_auth.dotenv.set_key")
    def test_callback_success(self, mock_set_key, MockKiteConnect):
        # Setup mock for KiteConnect
        mock_kite = MockKiteConnect.return_value
        mock_kite.generate_session.return_value = {
            "access_token": "valid_access_token",
            "user_id": "user123"
        }

        # Mock query params
        params = {
            "request_token": "test_request_token",
            "status": "success",
            "action": "login"
        }

        # Make request to callback endpoint
        response = self.client.get("/auth/kite/callback", params=params)

        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertIn("Authentication Successful", response.text)

        # Verify token exchange happened
        mock_kite.generate_session.assert_called_with("test_request_token", api_secret="test_secret")

        # Verify persistence (checking if set_key was called)
        # Note: We can't easily verify the file update in integration test without side effects,
        # so mocking set_key is the right approach to verify INTENT.
        # We assume .env is used as per KiteAuth implementation.
        mock_set_key.assert_called()
        args, _ = mock_set_key.call_args
        self.assertEqual(args[1], "KITE_ACCESS_TOKEN")
        self.assertEqual(args[2], "valid_access_token")

    @patch.dict(os.environ, {
        "KITE_API_KEY": "test_key",
        "KITE_API_SECRET": "test_secret"
    })
    def test_callback_failure_status(self):
        params = {
            "request_token": "test_request_token",
            "status": "failure"
        }

        response = self.client.get("/auth/kite/callback", params=params)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Auth Failed", response.text)

    def test_callback_missing_token(self):
        params = {
            "status": "success"
        }

        response = self.client.get("/auth/kite/callback", params=params)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing request_token", response.text)
