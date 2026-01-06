import unittest
from unittest.mock import MagicMock, patch, Mock
import threading
import http.client
import time
import sys
import os
from scripts.kite_auth_bootstrap import CallbackHandler, main
import http.server

class TestBootstrapIntegration(unittest.TestCase):
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
    def test_check_only_with_valid_session(self, mock_kite_connect):
        """Test --check-only flag exits with status 0 when session is valid."""
        # Mock valid session
        mock_instance = mock_kite_connect.return_value
        mock_instance.profile.return_value = {"user_id": "123"}
        
        # Test should exit with 0
        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 0)

    @patch.dict(os.environ, {
        "KITE_API_KEY": "test_api_key",
        "KITE_API_SECRET": "test_api_secret",
        "KITE_ACCESS_TOKEN": "test_access_token"
    })
    @patch('src.auth.kite_auth.KiteConnect')
    @patch('sys.argv', ['kite_auth_bootstrap.py', '--check-only'])
    def test_check_only_with_invalid_session(self, mock_kite_connect):
        """Test --check-only flag exits with status 1 when session is invalid."""
        # Mock invalid session
        mock_instance = mock_kite_connect.return_value
        mock_instance.profile.side_effect = Exception("Token invalid")
        mock_instance.login_url.return_value = "https://kite.trade/connect/login"
        
        # Test should exit with 1
        with self.assertRaises(SystemExit) as cm:
            main()
        self.assertEqual(cm.exception.code, 1)

    @patch.dict(os.environ, {
        "KITE_API_KEY": "test_api_key",
        "KITE_API_SECRET": "test_api_secret",
        "KITE_ACCESS_TOKEN": "test_access_token"
    })
    @patch('src.auth.kite_auth.KiteConnect')
    @patch('http.server.HTTPServer')
    @patch('sys.argv', ['kite_auth_bootstrap.py', '--port', '9090'])
    def test_custom_port_argument(self, mock_http_server, mock_kite_connect):
        """Test --port argument is properly used by the callback server."""
        # Mock invalid session to trigger server start
        mock_instance = mock_kite_connect.return_value
        mock_instance.profile.side_effect = Exception("Token invalid")
        mock_instance.login_url.return_value = "https://kite.trade/connect/login"
        
        # Create a mock server that simulates receiving a callback token
        mock_server_instance = Mock()
        # Initially no token, matching the behavior in main()
        mock_server_instance.request_token = None
        
        # When handle_request is called, set the token to simulate receiving callback
        def side_effect_set_token():
            mock_server_instance.request_token = "test_token"
        
        mock_server_instance.handle_request = Mock(side_effect=side_effect_set_token)
        mock_server_instance.server_close = Mock()
        mock_http_server.return_value = mock_server_instance
        
        # Mock token exchange and persist
        mock_instance.generate_session.return_value = {
            "access_token": "new_token",
            "user_id": "123"
        }
        
        with patch('src.auth.kite_auth.dotenv'):
            try:
                main()
            except SystemExit:
                pass
        
        # Verify HTTPServer was called with the custom port
        mock_http_server.assert_called_once_with(('localhost', 9090), CallbackHandler)

if __name__ == '__main__':
    unittest.main()
