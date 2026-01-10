import pytest
from unittest.mock import MagicMock, patch
import logging
from apps.api.routes.kite_auth import kite_callback
from fastapi import Request
from fastapi.responses import HTMLResponse

class TestAuthLogging:

    @pytest.fixture
    def mock_request(self):
        def _make_request(params):
            request = MagicMock(spec=Request)
            request.query_params = params
            return request
        return _make_request

    @patch("apps.api.routes.kite_auth.logger")
    @pytest.mark.asyncio
    async def test_callback_logs_masked_token_on_failure(self, mock_logger, mock_request):
        """Test that request_token is masked in logs on failure"""
        params = {"status": "failure", "request_token": "secret_token_123"}
        request = mock_request(params)

        await kite_callback(request)

        # Verify logger was called
        assert mock_logger.error.called

        # Verify the message does NOT contain the secret token
        log_message = mock_logger.error.call_args[0][0]
        assert "secret_token_123" not in log_message
        assert "***" in log_message

    @patch("apps.api.routes.kite_auth.logger")
    @patch("apps.api.routes.kite_auth.KiteAuth")
    @pytest.mark.asyncio
    async def test_callback_logs_success_safe(self, mock_kite_auth, mock_logger, mock_request):
        """Test success path logs are safe"""
        params = {"status": "success", "request_token": "secret_token_123"}
        request = mock_request(params)

        mock_auth = mock_kite_auth.return_value
        mock_auth.exchange_request_token.return_value = "access_token_abc"

        await kite_callback(request)

        # Check all info logs
        for call in mock_logger.info.call_args_list:
            msg = call[0][0]
            assert "secret_token_123" not in msg
            assert "access_token_abc" not in msg

    @patch("src.auth.kite_auth.logger")
    @patch("src.auth.kite_auth.dotenv")
    def test_persist_token_logging_safe(self, mock_dotenv, mock_logger):
        """Test that persisting token doesn't log the token itself"""
        from src.auth.kite_auth import KiteAuth

        with patch("src.auth.kite_auth.KiteConnect"):
            auth = KiteAuth()
            auth.persist_access_token("secret_access_token")

            # Verify logs
            for call in mock_logger.info.call_args_list:
                msg = call[0][0]
                assert "secret_access_token" not in msg
