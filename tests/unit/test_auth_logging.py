import logging
import pytest
from unittest.mock import patch
import io
from src.auth.kite_auth import KiteAuth

def test_logs_do_not_contain_secrets():
    # Setup logger capture
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("src.auth.kite_auth")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    secret_token = "SECRET_TOKEN_12345"

    with patch("src.auth.kite_auth.KiteConnect") as MockKite:
        instance = MockKite.return_value
        instance.generate_session.return_value = {"access_token": secret_token}

        auth = KiteAuth()
        # Mock api_secret to allow exchange
        auth.api_secret = "test_secret"

        # Perform exchange which logs messages
        with patch.object(auth, 'persist_access_token'):
            auth.exchange_request_token("req_token")

    # Check logs
    log_contents = stream.getvalue()

    # Assert secret is NOT in logs
    assert secret_token not in log_contents
    assert "SECRET_TOKEN_12345" not in log_contents

    # Clean up
    logger.removeHandler(handler)
