import threading
import time
import requests
import pytest
from scripts.kite_auth_bootstrap import wait_for_callback, CALLBACK_PORT, CALLBACK_PATH

def test_callback_server():
    """Integration test for the callback server"""

    # Start server in a separate thread
    result_container = {}

    def run_server():
        result_container['token'] = wait_for_callback(port=CALLBACK_PORT)

    server_thread = threading.Thread(target=run_server)
    server_thread.start()

    # Wait for server to start with retries
    max_retries = 10
    url = f"http://localhost:{CALLBACK_PORT}{CALLBACK_PATH}?request_token=test_request_token_123"

    for i in range(max_retries):
        try:
            # Check if port is open first or just try request
            response = requests.get(url, timeout=1)
            assert response.status_code == 200
            assert "Auth Success" in response.text
            break
        except requests.exceptions.ConnectionError:
            if i == max_retries - 1:
                pytest.fail("Could not connect to callback server")
            time.sleep(0.5)
        except Exception as e:
            pytest.fail(f"Request failed: {e}")

    # Wait for server to shut down
    server_thread.join(timeout=2)

    assert result_container.get('token') == "test_request_token_123"

def test_callback_server_missing_token():
    """Test callback server with missing token"""
    # Start server in a separate thread
    result_container = {}
    shutdown_event = threading.Event()

    def run_server():
        result_container['token'] = wait_for_callback(port=CALLBACK_PORT)
        shutdown_event.set()

    server_thread = threading.Thread(target=run_server)
    server_thread.start()

    # Wait for server to start with retries
    max_retries = 10
    url = f"http://localhost:{CALLBACK_PORT}{CALLBACK_PATH}"  # No request_token param

    try:
        for i in range(max_retries):
            try:
                # Request without request_token should get a 400 response
                response = requests.get(url, timeout=1)
                assert response.status_code == 400
                assert b"Missing request_token" in response.content
                
                # Server should not capture any token
                time.sleep(0.1)  # Give time for any processing
                assert result_container.get('token') is None
                break
            except requests.exceptions.ConnectionError:
                if i == max_retries - 1:
                    pytest.fail("Could not connect to callback server")
                time.sleep(0.5)
            except Exception as e:
                pytest.fail(f"Request failed: {e}")
    finally:
        # Clean up: the server won't shutdown automatically since no valid token was received
        # We need to force close it by making a connection or waiting with timeout
        server_thread.join(timeout=1.0)
        if server_thread.is_alive():
            # Server is still running, which is expected for this test case
            pass
