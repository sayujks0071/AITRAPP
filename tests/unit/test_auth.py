import pytest
from unittest.mock import Mock, patch
from src.auth.kite_auth import KiteAuth
from kiteconnect.exceptions import TokenException

class TestKiteAuth:
    @pytest.fixture
    def mock_settings(self, mocker):
        mocker.patch("src.auth.kite_auth.settings.kite_api_key", "test_key")
        mocker.patch("src.auth.kite_auth.settings.kite_api_secret", "test_secret")
        mocker.patch("src.auth.kite_auth.settings.kite_access_token", "test_token")
        mocker.patch("src.auth.kite_auth.settings.kite_user_id", "test_user")

    @pytest.fixture
    def kite_auth(self, mock_settings):
        with patch("src.auth.kite_auth.KiteConnect") as mock_kite:
            auth = KiteAuth()
            auth.kite = mock_kite.return_value
            return auth

    def test_is_session_valid_success(self, kite_auth):
        kite_auth.kite.profile.return_value = {"status": "success"}
        assert kite_auth.is_session_valid() is True

    def test_is_session_valid_failure(self, kite_auth):
        kite_auth.kite.profile.side_effect = TokenException("Invalid token")
        assert kite_auth.is_session_valid() is False

    def test_exchange_request_token_success(self, kite_auth):
        expected_data = {
            "access_token": "new_token",
            "user_id": "test_user",
            "public_token": "public"
        }
        kite_auth.kite.generate_session.return_value = expected_data

        data = kite_auth.exchange_request_token("req_token")

        assert data == expected_data
        kite_auth.kite.generate_session.assert_called_with("req_token", api_secret="test_secret")
        kite_auth.kite.set_access_token.assert_called_with("new_token")

    def test_exchange_request_token_failure(self, kite_auth):
        kite_auth.kite.generate_session.side_effect = Exception("Exchange failed")

        with pytest.raises(Exception, match="Exchange failed"):
            kite_auth.exchange_request_token("bad_token")
