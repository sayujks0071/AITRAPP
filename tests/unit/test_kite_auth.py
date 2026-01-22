import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Ensure src is in python path
sys.path.insert(0, os.getcwd())

from src.auth.kite_auth import KiteAuth
from kiteconnect import exceptions

class TestKiteAuth(unittest.TestCase):

    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {
            "KITE_API_KEY": "test_api_key",
            "KITE_API_SECRET": "test_api_secret",
            "KITE_ACCESS_TOKEN": "test_access_token"
        })
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    @patch("src.auth.kite_auth.KiteConnect")
    def test_is_session_valid_success(self, mock_kite_cls):
        mock_kite = mock_kite_cls.return_value
        mock_kite.profile.return_value = {"status": "success"}

        auth = KiteAuth()
        self.assertTrue(auth.is_session_valid())
        mock_kite.profile.assert_called_once()

    @patch("src.auth.kite_auth.KiteConnect")
    def test_is_session_valid_failure_token_exception(self, mock_kite_cls):
        mock_kite = mock_kite_cls.return_value
        mock_kite.profile.side_effect = exceptions.TokenException("Invalid token")

        auth = KiteAuth()
        self.assertFalse(auth.is_session_valid())

    @patch("src.auth.kite_auth.KiteConnect")
    def test_is_session_valid_no_token(self, mock_kite_cls):
        with patch.dict(os.environ, {}, clear=True):
            # If env is empty, init might warn but continue.
            # We explicitly set access_token to None for this test case if needed,
            # but KiteAuth loads from env in __init__.

            # Let's override the loaded token
            auth = KiteAuth()
            auth.access_token = None

            self.assertFalse(auth.is_session_valid())

    @patch("src.auth.kite_auth.KiteConnect")
    def test_get_login_url(self, mock_kite_cls):
        mock_kite = mock_kite_cls.return_value
        mock_kite.login_url.return_value = "https://kite.trade/connect/login?api_key=test_api_key"

        auth = KiteAuth()
        url = auth.get_login_url()
        self.assertEqual(url, "https://kite.trade/connect/login?api_key=test_api_key")

    @patch("src.auth.kite_auth.KiteConnect")
    @patch("src.auth.kite_auth.dotenv")
    def test_exchange_request_token_success(self, mock_dotenv, mock_kite_cls):
        mock_kite = mock_kite_cls.return_value
        mock_kite.generate_session.return_value = {"access_token": "new_access_token"}

        auth = KiteAuth()
        token = auth.exchange_request_token("request_token_123")

        self.assertEqual(token, "new_access_token")
        self.assertEqual(auth.access_token, "new_access_token")
        mock_kite.set_access_token.assert_called_with("new_access_token")

    @patch("src.auth.kite_auth.KiteConnect")
    @patch("src.auth.kite_auth.dotenv")
    def test_persist_access_token(self, mock_dotenv, mock_kite_cls):
        mock_dotenv.find_dotenv.return_value = ".env.test"

        auth = KiteAuth()
        auth.persist_access_token("persisted_token")

        mock_dotenv.set_key.assert_called_with(".env.test", "KITE_ACCESS_TOKEN", "persisted_token")
        self.assertEqual(os.environ["KITE_ACCESS_TOKEN"], "persisted_token")

if __name__ == '__main__':
    unittest.main()
