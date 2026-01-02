import pytest
from unittest.mock import Mock, patch
from packages.core.auth.kite_auth import KiteAuth

@pytest.fixture
def mock_kite_connect(mocker):
    return mocker.patch("packages.core.auth.kite_auth.KiteConnect")

@pytest.fixture
def mock_settings(mocker):
    return mocker.patch("packages.core.auth.kite_auth.settings")

class TestKiteAuth:
    def test_init_loads_settings(self, mock_settings):
        mock_settings.kite_api_key = "key"
        mock_settings.kite_api_secret = "secret"
        mock_settings.kite_access_token = "token"

        auth = KiteAuth()
        assert auth.api_key == "key"
        assert auth.api_secret == "secret"
        assert auth.access_token == "token"

    def test_is_session_valid_true(self, mock_kite_connect, mock_settings):
        mock_instance = mock_kite_connect.return_value
        auth = KiteAuth()

        result = auth.is_session_valid()

        mock_instance.profile.assert_called_once()
        assert result is True

    def test_is_session_valid_false_on_exception(self, mock_kite_connect):
        mock_instance = mock_kite_connect.return_value
        mock_instance.profile.side_effect = Exception("Auth failed")
        auth = KiteAuth()

        result = auth.is_session_valid()

        assert result is False

    def test_is_session_valid_false_no_token(self, mock_settings):
        mock_settings.kite_access_token = None
        auth = KiteAuth()
        assert auth.is_session_valid() is False

    def test_get_login_url(self, mock_kite_connect):
        mock_instance = mock_kite_connect.return_value
        mock_instance.login_url.return_value = "http://login"
        auth = KiteAuth()

        url = auth.get_login_url()
        assert url == "http://login"

    def test_exchange_request_token(self, mock_kite_connect, mock_settings):
        mock_instance = mock_kite_connect.return_value
        mock_instance.generate_session.return_value = {"access_token": "new_token"}
        mock_settings.kite_api_secret = "secret"

        auth = KiteAuth()
        token = auth.exchange_request_token("request_token")

        assert token == "new_token"
        mock_instance.generate_session.assert_called_with("request_token", api_secret="secret")

    def test_persist_access_token(self, tmp_path, mocker):
        # Mock Path to return a temp .env file
        env_file = tmp_path / ".env"
        env_file.write_text("KITE_ACCESS_TOKEN=old_token\nOTHER=val")

        mocker.patch("pathlib.Path.resolve", return_value=tmp_path)
        # We need to mock parents to return [..., tmp_path] or similar
        # Actually, simpler to just mock the exact file path finding logic or write to a real temp file
        # But `persist_access_token` does `Path(__file__).resolve().parents[3]`

        # Let's mock `Path` in the module
        with patch("packages.core.auth.kite_auth.Path") as mock_path:
            mock_path.return_value.resolve.return_value.parents = [None, None, None, tmp_path]
            mock_path.return_value.resolve.return_value.__file__ = "mocked"

            # Since we are mocking Path, we need to handle the __file__ usage in the code if any
            # The code uses Path(__file__)

            auth = KiteAuth()
            auth.persist_access_token("new_token")

            content = env_file.read_text()
            assert "KITE_ACCESS_TOKEN=new_token" in content
            assert "OTHER=val" in content

    def test_persist_access_token_appends(self, tmp_path, mocker):
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER=val")

        with patch("packages.core.auth.kite_auth.Path") as mock_path:
            mock_path.return_value.resolve.return_value.parents = [None, None, None, tmp_path]

            auth = KiteAuth()
            auth.persist_access_token("new_token")

            content = env_file.read_text()
            assert "KITE_ACCESS_TOKEN=new_token" in content
