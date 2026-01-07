import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
from src.auth.kite_auth import KiteAuth

class TestKiteAuth(unittest.TestCase):

    def setUp(self):
        # Setup environment variables for testing
        self.env_patcher = patch.dict(os.environ, {
            "KITE_API_KEY": "test_api_key",
            "KITE_API_SECRET": "test_api_secret",
            "KITE_ACCESS_TOKEN": "test_access_token"
        })
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    @patch("src.auth.kite_auth.KiteConnect")
    def test_init(self, mock_kite_connect):
        auth = KiteAuth()
        self.assertEqual(auth.api_key, "test_api_key")
        self.assertEqual(auth.api_secret, "test_api_secret")
        self.assertEqual(auth.access_token, "test_access_token")
        mock_kite_connect.assert_called_with(api_key="test_api_key", access_token="test_access_token")

    @patch("src.auth.kite_auth.KiteConnect")
    def test_is_session_valid_success(self, mock_kite_connect):
        mock_instance = mock_kite_connect.return_value
        mock_instance.profile.return_value = {"user_id": "123"}

        auth = KiteAuth()
        self.assertTrue(auth.is_session_valid())

    @patch("src.auth.kite_auth.KiteConnect")
    def test_is_session_valid_failure(self, mock_kite_connect):
        mock_instance = mock_kite_connect.return_value
        mock_instance.profile.side_effect = Exception("Token invalid")

        auth = KiteAuth()
        self.assertFalse(auth.is_session_valid())

    @patch("src.auth.kite_auth.KiteConnect")
    def test_get_login_url(self, mock_kite_connect):
        mock_instance = mock_kite_connect.return_value
        mock_instance.login_url.return_value = "https://kite.trade/login"

        auth = KiteAuth()
        self.assertEqual(auth.get_login_url(), "https://kite.trade/login")

    @patch("src.auth.kite_auth.KiteConnect")
    def test_exchange_request_token(self, mock_kite_connect):
        mock_instance = mock_kite_connect.return_value
        mock_instance.generate_session.return_value = {
            "access_token": "new_access_token",
            "user_id": "123"
        }

        auth = KiteAuth()
        token = auth.exchange_request_token("req_token")

        self.assertEqual(token, "new_access_token")
        self.assertEqual(auth.access_token, "new_access_token")
        mock_instance.generate_session.assert_called_with("req_token", api_secret="test_api_secret")
        mock_instance.set_access_token.assert_called_with("new_access_token")

    @patch("src.auth.kite_auth.dotenv")
    def test_persist_access_token(self, mock_dotenv):
        mock_dotenv.find_dotenv.return_value = ".env"

        auth = KiteAuth() # Uses setup env
        auth.persist_access_token("new_persisted_token")

        mock_dotenv.set_key.assert_called_with(".env", "KITE_ACCESS_TOKEN", "new_persisted_token")
        self.assertEqual(os.environ["KITE_ACCESS_TOKEN"], "new_persisted_token")

if __name__ == '__main__':
    unittest.main()
