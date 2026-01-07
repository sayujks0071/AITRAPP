import pytest
from unittest.mock import MagicMock, patch
import os
from src.auth.kite_auth import KiteAuth

class TestKiteAuth:

    @pytest.fixture
    def mock_env(self):
        with patch.dict(os.environ, {
            "KITE_API_KEY": "test_key",
            "KITE_API_SECRET": "test_secret",
            "KITE_ACCESS_TOKEN": "test_token"
        }):
            yield

    @pytest.fixture
    def kite_auth(self, mock_env):
        with patch("src.auth.kite_auth.KiteConnect") as MockKite:
            instance = MockKite.return_value
            # Setup default behaviors
            instance.login_url.return_value = "https://kite.trade/connect/login?api_key=test_key"
            yield KiteAuth()

    def test_init(self, mock_env):
        with patch("src.auth.kite_auth.KiteConnect") as MockKite:
            auth = KiteAuth()
            assert auth.api_key == "test_key"
            assert auth.api_secret == "test_secret"
            assert auth.access_token == "test_token"
            MockKite.assert_called_with(api_key="test_key", access_token="test_token")

    def test_is_session_valid_true(self, kite_auth):
        kite_auth.kite.profile.return_value = {"user_id": "test_user"}
        assert kite_auth.is_session_valid() is True

    def test_is_session_valid_false_exception(self, kite_auth):
        kite_auth.kite.profile.side_effect = Exception("Token invalid")
        assert kite_auth.is_session_valid() is False

    def test_is_session_valid_no_token(self, mock_env):
        with patch("src.auth.kite_auth.KiteConnect"):
            auth = KiteAuth()
            auth.access_token = None
            assert auth.is_session_valid() is False

    def test_get_login_url(self, kite_auth):
        url = kite_auth.get_login_url()
        assert "api_key=test_key" in url

    def test_exchange_request_token_success(self, kite_auth):
        kite_auth.kite.generate_session.return_value = {"access_token": "new_access_token"}

        token = kite_auth.exchange_request_token("request_token_123")

        assert token == "new_access_token"
        assert kite_auth.access_token == "new_access_token"
        kite_auth.kite.generate_session.assert_called_with("request_token_123", api_secret="test_secret")
        kite_auth.kite.set_access_token.assert_called_with("new_access_token")

    @patch("src.auth.kite_auth.dotenv")
    def test_persist_access_token(self, mock_dotenv, kite_auth):
        mock_dotenv.find_dotenv.return_value = ".env.test"

        kite_auth.persist_access_token("persisted_token")

        mock_dotenv.set_key.assert_called_with(".env.test", "KITE_ACCESS_TOKEN", "persisted_token")
        assert os.environ["KITE_ACCESS_TOKEN"] == "persisted_token"
