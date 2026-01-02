import threading
import time
import requests
import pytest
from unittest.mock import MagicMock, patch
from http.server import HTTPServer
from scripts.kite_auth_bootstrap import CallbackHandler, run_auth_flow

# Use a random high port for testing to avoid conflicts
TEST_PORT = 8089

@pytest.fixture
def mock_server():
    server = HTTPServer(("localhost", TEST_PORT), CallbackHandler)
    server.request_token = None
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    yield server
    server.shutdown()
    server.server_close()

def test_callback_handler_success(mock_server):
    """Test that the callback handler correctly parses request_token"""
    callback_url = f"http://localhost:{TEST_PORT}/callback?request_token=test_token_123"
    response = requests.get(callback_url)

    assert response.status_code == 200
    assert "Auth Success" in response.text
    assert mock_server.request_token == "test_token_123"

def test_callback_handler_missing_token(mock_server):
    """Test that the callback handler returns 400 if request_token is missing"""
    callback_url = f"http://localhost:{TEST_PORT}/callback?other_param=123"
    response = requests.get(callback_url)

    assert response.status_code == 400
    assert "Missing request_token" in response.text
    assert mock_server.request_token is None

def test_callback_handler_invalid_path(mock_server):
    """Test that the callback handler returns 404 for other paths"""
    callback_url = f"http://localhost:{TEST_PORT}/other"
    response = requests.get(callback_url)

    assert response.status_code == 404

@patch("scripts.kite_auth_bootstrap.KiteAuth")
@patch("scripts.kite_auth_bootstrap.webbrowser")
@patch("scripts.kite_auth_bootstrap.socketserver.TCPServer")
@patch("scripts.kite_auth_bootstrap.print") # suppress print
def test_run_auth_flow_full(mock_print, mock_server_cls, mock_webbrowser, MockKiteAuth):
    """
    Test the full flow:
    1. Session invalid
    2. Start server
    3. Simulate callback
    4. Exchange & Persist
    """
    # Setup mocks
    auth_instance = MockKiteAuth.return_value
    auth_instance.is_session_valid.return_value = False
    auth_instance.get_login_url.return_value = "http://login.url"
    auth_instance.exchange_request_token.return_value = "access_token_123"

    # Mock server instance
    server_instance = mock_server_cls.return_value
    server_instance.__enter__.return_value = server_instance

    # Simulate callback happening by setting request_token
    # We need to make serve_forever run briefly then stop or simulate the token appearing
    def side_effect_serve_forever():
        # Simulate wait time and then token arrival
        time.sleep(0.1)
        server_instance.request_token = "req_token_xyz"

    server_instance.serve_forever.side_effect = side_effect_serve_forever
    server_instance.request_token = None # Start as None

    # We also need to handle the wait loop in run_auth_flow
    # The loop waits for httpd.request_token to be set

    # However, since run_auth_flow runs serve_forever in a thread,
    # we can just set request_token in the mock object that run_auth_flow holds.
    # But wait, run_auth_flow creates the server instance.

    # To properly simulate the loop:
    # run_auth_flow:
    #   httpd = TCPServer(...)
    #   thread = Thread(target=httpd.serve_forever)
    #   thread.start()
    #   while httpd.request_token is None: ...

    # If we mock TCPServer, we control the instance.

    def serve_forever_impl():
        time.sleep(0.1)
        server_instance.request_token = "got_it"

    server_instance.serve_forever = serve_forever_impl

    # We need to make sure the thread logic works.
    # run_auth_flow starts a thread targeting serve_forever.
    # Our mock serve_forever will set the token.

    ret = run_auth_flow()

    assert ret == 0
    auth_instance.is_session_valid.assert_called_once()
    auth_instance.get_login_url.assert_called_once()
    mock_webbrowser.open.assert_called_with("http://login.url")
    auth_instance.exchange_request_token.assert_called_with("got_it")
    auth_instance.persist_access_token.assert_called_with("access_token_123")
