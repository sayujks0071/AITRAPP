import pytest
from unittest.mock import patch
from packages.core.auth.kite_auth import KiteAuth

@pytest.fixture
def mock_kite_connect():
    with patch('packages.core.auth.kite_auth.KiteConnect') as MockKite:
        yield MockKite

@pytest.fixture
def auth_module(mock_kite_connect):
    # Setup settings mock if needed, but KiteAuth reads from settings which reads env
    # For unit test we can rely on KiteAuth initializing with mocked settings or defaults
    return KiteAuth()

def test_is_session_valid_true(auth_module, mock_kite_connect):
    # Setup
    auth_module.kite.profile.return_value = {"user_id": "AB1234"}
    auth_module.access_token = "valid_token"

    # Execute
    assert auth_module.is_session_valid() is True
    auth_module.kite.profile.assert_called_once()

def test_is_session_valid_false_exception(auth_module, mock_kite_connect):
    from kiteconnect.exceptions import TokenException

    # Setup
    auth_module.kite.profile.side_effect = TokenException("Token expired")
    auth_module.access_token = "invalid_token"

    # Execute
    assert auth_module.is_session_valid() is False

def test_is_session_valid_false_no_token(auth_module):
    # Setup
    auth_module.access_token = None

    # Execute
    assert auth_module.is_session_valid() is False

def test_get_login_url(auth_module, mock_kite_connect):
    auth_module.kite.login_url.return_value = "https://kite.trade/connect/login?v=3"
    assert auth_module.get_login_url() == "https://kite.trade/connect/login?v=3"

def test_exchange_request_token_success(auth_module, mock_kite_connect):
    # Setup
    auth_module.kite.generate_session.return_value = {
        "access_token": "new_access_token",
        "user_id": "AB1234"
    }

    # Execute
    token = auth_module.exchange_request_token("request_token_123")

    # Verify
    assert token == "new_access_token"
    auth_module.kite.generate_session.assert_called_with("request_token_123", api_secret=auth_module.api_secret)

def test_exchange_request_token_failure(auth_module, mock_kite_connect):
    # Setup
    auth_module.kite.generate_session.side_effect = Exception("Network Error")

    # Execute & Verify
    with pytest.raises(Exception):
        auth_module.exchange_request_token("bad_token")

@patch("packages.core.auth.kite_auth.set_key")
def test_persist_access_token(mock_set_key, auth_module):
    # Execute
    auth_module.persist_access_token("new_token_456")

    # Verify
    assert auth_module.access_token == "new_token_456"
    mock_set_key.assert_called_with(".env", "KITE_ACCESS_TOKEN", "new_token_456")
