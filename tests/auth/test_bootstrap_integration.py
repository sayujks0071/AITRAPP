import unittest
from unittest.mock import MagicMock, patch, call
import threading
import http.client
import time
import sys
import os
from scripts.kite_auth_bootstrap import CallbackHandler, main
import http.server

class TestBootstrapIntegration(unittest.TestCase):
    def _setup_mock_server_with_token(self, mock_http_server):
        """Helper to setup a mock server that simulates token reception."""
        mock_server_instance = MagicMock()
        # Initially request_token is None, after one handle_request call it should have a value
        mock_server_instance.request_token = None
        
        def set_token_on_first_call(*args, **kwargs):
            # Simulate receiving token after first handle_request
            mock_server_instance.request_token = "test_token"
        
        mock_server_instance.handle_request = set_token_on_first_call
        mock_http_server.return_value = mock_server_instance
        return mock_server_instance

    def test_callback_server(self):
        # Start a real server on a random port
        port = 0 # random port
        server = http.server.HTTPServer(('localhost', port), CallbackHandler)
        server.request_token = None
        assigned_port = server.server_port

        server_thread = threading.Thread(target=server.handle_request)
        server_thread.start()

        # Make a request
        conn = http.client.HTTPConnection('localhost', assigned_port)
        conn.request("GET", "/callback?request_token=test_token_123")
        response = conn.getresponse()

        # Check response
        self.assertEqual(response.status, 200)
        content = response.read().decode()
        self.assertIn("Auth Success", content)

        # Wait for thread to join (handle_request handles one request)
        server_thread.join(timeout=1)

        # Check if token captured
        self.assertEqual(server.request_token, "test_token_123")

        server.server_close()

    @patch.dict(os.environ, {
        "KITE_API_KEY": "test_api_key",
        "KITE_API_SECRET": "test_api_secret",
        "KITE_ACCESS_TOKEN": "test_access_token"
    })
    @patch('src.auth.kite_auth.KiteConnect')
    @patch('sys.argv', ['kite_auth_bootstrap.py', '--check-only'])
    def test_check_only_mode_valid_session(self, mock_kite_connect):
        """Test that --check-only exits with status 0 when session is valid."""
        # Mock valid session
        mock_instance = mock_kite_connect.return_value
        mock_instance.profile.return_value = {"user_id": "123"}

        # main() should call sys.exit(0) for valid session
        with self.assertRaises(SystemExit) as cm:
            main()
        
        self.assertEqual(cm.exception.code, 0)

    @patch.dict(os.environ, {
        "KITE_API_KEY": "test_api_key",
        "KITE_API_SECRET": "test_api_secret",
        "KITE_ACCESS_TOKEN": "invalid_token"
    })
    @patch('src.auth.kite_auth.KiteConnect')
    @patch('sys.argv', ['kite_auth_bootstrap.py', '--check-only'])
    def test_check_only_mode_invalid_session(self, mock_kite_connect):
        """Test that --check-only exits with status 1 when session is invalid."""
        # Mock invalid session
        mock_instance = mock_kite_connect.return_value
        mock_instance.profile.side_effect = Exception("Token invalid")
        mock_instance.login_url.return_value = "https://kite.trade/login"

        # main() should call sys.exit(1) for invalid session in check-only mode
        with self.assertRaises(SystemExit) as cm:
            main()
        
        self.assertEqual(cm.exception.code, 1)

    @patch.dict(os.environ, {
        "KITE_API_KEY": "test_api_key",
        "KITE_API_SECRET": "test_api_secret",
        "KITE_ACCESS_TOKEN": "invalid_token"
    })
    @patch('src.auth.kite_auth.KiteConnect')
    @patch('sys.argv', ['kite_auth_bootstrap.py', '--port', '9090'])
    @patch('http.server.HTTPServer')
    def test_custom_port_argument(self, mock_http_server, mock_kite_connect):
        """Test that --port argument is properly used by the callback server."""
        # Mock invalid session to trigger server setup
        mock_instance = mock_kite_connect.return_value
        mock_instance.profile.side_effect = Exception("Token invalid")
        mock_instance.login_url.return_value = "https://kite.trade/login"
        
        # Setup mock server using helper
        self._setup_mock_server_with_token(mock_http_server)
        
        # Mock token exchange (generate_session is called by exchange_request_token)
        mock_instance.generate_session.return_value = {
            "access_token": "new_token",
            "user_id": "123"
        }
        
        # Mock dotenv to prevent actual file writes
        with patch('src.auth.kite_auth.dotenv.find_dotenv', return_value=".env"), \
             patch('src.auth.kite_auth.dotenv.set_key'):
            try:
                main()
            except SystemExit:
                pass
        
        # Verify HTTPServer was called with the custom port 9090
        mock_http_server.assert_called_once()
        call_args = mock_http_server.call_args
        self.assertEqual(call_args[0][0], ('localhost', 9090))

    @patch.dict(os.environ, {
        "KITE_API_KEY": "test_api_key",
        "KITE_API_SECRET": "test_api_secret",
        "KITE_ACCESS_TOKEN": "invalid_token"
    })
    @patch('src.auth.kite_auth.KiteConnect')
    @patch('sys.argv', ['kite_auth_bootstrap.py'])
    @patch('http.server.HTTPServer')
    def test_default_port_when_not_specified(self, mock_http_server, mock_kite_connect):
        """Test that default port 8080 is used when --port is not specified."""
        # Mock invalid session to trigger server setup
        mock_instance = mock_kite_connect.return_value
        mock_instance.profile.side_effect = Exception("Token invalid")
        mock_instance.login_url.return_value = "https://kite.trade/login"
        
        # Setup mock server using helper
        self._setup_mock_server_with_token(mock_http_server)
        
        # Mock token exchange (generate_session is called by exchange_request_token)
        mock_instance.generate_session.return_value = {
            "access_token": "new_token",
            "user_id": "123"
        }
        
        # Mock dotenv to prevent actual file writes
        with patch('src.auth.kite_auth.dotenv.find_dotenv', return_value=".env"), \
             patch('src.auth.kite_auth.dotenv.set_key'):
            try:
                main()
            except SystemExit:
                pass
        
        # Verify HTTPServer was called with default port 8080
        mock_http_server.assert_called_once()
        call_args = mock_http_server.call_args
        self.assertEqual(call_args[0][0], ('localhost', 8080))

if __name__ == '__main__':
    unittest.main()
