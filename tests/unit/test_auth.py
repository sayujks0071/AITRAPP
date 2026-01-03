import pytest
import os
from unittest.mock import patch, MagicMock

# Set up test environment variables before any imports
os.environ.setdefault('KITE_API_KEY', 'test_api_key')
os.environ.setdefault('KITE_API_SECRET', 'test_api_secret')
os.environ.setdefault('KITE_ACCESS_TOKEN', 'test_access_token')
os.environ.setdefault('KITE_USER_ID', 'test_user_id')
os.environ.setdefault('DATABASE_URL', 'sqlite:///./test.db')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('API_SECRET_KEY', 'test_secret_key')

from packages.core.auth.kite_auth import KiteAuth

@pytest.fixture
def mock_kite_connect():
    with patch('packages.core.auth.kite_auth.KiteConnect') as MockKite:
        yield MockKite

@pytest.fixture
def auth_module(mock_kite_connect):
    # KiteAuth will use the test environment variables set above
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
    network_error = Exception("Network Error")
    auth_module.kite.generate_session.side_effect = network_error

    # Execute & Verify - should raise the specific exception
    with pytest.raises(Exception) as exc_info:
        auth_module.exchange_request_token("bad_token")
    
    assert str(exc_info.value) == "Network Error"

@patch("packages.core.auth.kite_auth.set_key")
@patch("packages.core.auth.kite_auth.os.getenv")
def test_persist_access_token(mock_getenv, mock_set_key, auth_module):
    # Mock getenv to return the default path
    mock_getenv.return_value = None  # Will use default path
    
    # Execute
    auth_module.persist_access_token("new_token_456")

    # Verify
    assert auth_module.access_token == "new_token_456"
    mock_set_key.assert_called_once()
    # Check that set_key was called with KITE_ACCESS_TOKEN and the token
    args = mock_set_key.call_args[0]
    assert args[1] == "KITE_ACCESS_TOKEN"
    assert args[2] == "new_token_456"
