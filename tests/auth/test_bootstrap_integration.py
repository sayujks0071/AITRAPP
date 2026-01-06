import unittest
from unittest.mock import MagicMock, patch
import threading
import http.client
import time
from scripts.kite_auth_bootstrap import CallbackHandler
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

if __name__ == '__main__':
    unittest.main()
