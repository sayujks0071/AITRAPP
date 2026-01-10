import pytest
import logging
import os
from unittest.mock import MagicMock, patch
from src.auth.kite_auth import KiteAuth
# Import the route function directly.
# We need to mock Request object properly.
from apps.api.routes.kite_auth import kite_callback
from fastapi import Request

class TestAuthLogging:

    def test_kite_auth_logging_no_secrets(self, caplog):
        caplog.set_level(logging.INFO)

        with patch.dict(os.environ, {
            "KITE_API_KEY": "secret_api_key",
            "KITE_API_SECRET": "secret_api_secret",
            "KITE_ACCESS_TOKEN": "secret_access_token"
        }):
            with patch("src.auth.kite_auth.KiteConnect") as MockKite:
                # Test initialization logging
                auth = KiteAuth()

                # Test persist logging
                with patch("src.auth.kite_auth.dotenv") as mock_dotenv:
                    # We mock find_dotenv to return a fake path so it logs that path
                    mock_dotenv.find_dotenv.return_value = ".env.test"
                    auth.persist_access_token("new_secret_token")

        # Check logs
        for record in caplog.records:
            # Check that secrets are NOT present
            assert "secret_api_key" not in record.message
            assert "secret_api_secret" not in record.message
            assert "secret_access_token" not in record.message
            assert "new_secret_token" not in record.message

            # Check that we DO see the safe message
            if "Persisting access token" in record.message:
                assert ".env.test" in record.message

    @pytest.mark.asyncio
    async def test_callback_logging_no_secrets(self, caplog):
        caplog.set_level(logging.INFO)

        # Mock request
        request = MagicMock(spec=Request)
        request.query_params = {
            "request_token": "secret_request_token",
            "status": "success"
        }

        with patch("apps.api.routes.kite_auth.KiteAuth") as MockKiteAuth:
            mock_auth = MockKiteAuth.return_value
            mock_auth.exchange_request_token.return_value = "new_access_token"

            # Test success case
            await kite_callback(request)

            # Check logs
            for record in caplog.records:
                assert "secret_request_token" not in record.message
                assert "new_access_token" not in record.message

    @pytest.mark.asyncio
    async def test_callback_failure_logging_sanitized(self, caplog):
        caplog.set_level(logging.ERROR)

        # Mock request with failure
        request = MagicMock(spec=Request)
        # Even on failure, if request_token was sent, we shouldn't log it if possible
        request.query_params = {
            "request_token": "secret_request_token_leak",
            "status": "failure",
            "message": "Something went wrong"
        }

        # We expect this to return 400 (not raise)
        await kite_callback(request)

        # Check logs
        found_error_log = False
        for record in caplog.records:
            if record.levelno == logging.ERROR:
                found_error_log = True
                # This assertion ensures that if we log params, we sanitize them
                # OR we simply don't log the secret values
                assert "secret_request_token_leak" not in record.message

        assert found_error_log
