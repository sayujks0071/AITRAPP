#!/usr/bin/env python3
"""
Kite Daily Auth Assistant
Runs daily at 8:00 AM to ensure valid Kite Connect session.
"""
import sys
import os
import webbrowser
import structlog
import http.server
import socketserver
import urllib.parse
import threading
from typing import Optional

# Add project root to path
sys.path.append(os.getcwd())

from packages.core.auth.kite_auth import KiteAuth
from packages.core.config import settings

logger = structlog.get_logger(__name__)

CALLBACK_PORT = 8080
CALLBACK_PATH = "/callback"

class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    """Handles the redirect callback from Kite Connect"""

    request_token: Optional[str] = None

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path == CALLBACK_PATH:
            query_params = urllib.parse.parse_qs(parsed_url.query)

            if 'request_token' in query_params:
                CallbackHandler.request_token = query_params['request_token'][0]

                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"<h1>Auth Success!</h1><p>You can close this window.</p>")

                # Signal to main thread that we have the token
                threading.Thread(target=self.server.shutdown).start()
            else:
                self.send_response(400)
                self.wfile.write(b"Missing request_token")
        else:
            self.send_response(404)
            self.wfile.write(b"Not Found")

    def log_message(self, format, *args):
        # Suppress default logging
        pass

def wait_for_callback(port: int = 8080) -> Optional[str]:
    """Starts a local server and waits for the callback with request_token"""
    CallbackHandler.request_token = None

    # Allow address reuse to avoid "Address already in use" errors
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", port), CallbackHandler) as httpd:
        logger.info(f"Listening for callback on port {port}...")
        httpd.serve_forever()

    return CallbackHandler.request_token

def main():
    logger.info("Starting Kite Daily Auth Assistant")

    # 1. Initialize Auth Module
    auth = KiteAuth()

    # 2. Check if session is already valid
    if auth.is_session_valid():
        logger.info("✅ Current session is valid. No action needed.")
        sys.exit(0)

    logger.info("⚠️  Session invalid or expired. Initiating login flow...")

    # 3. Get Login URL
    login_url = auth.get_login_url()

    # 4. Prompt user (cannot automate login credentials)
    print("\n" + "="*60)
    print("ACTION REQUIRED: Manual Login")
    print("="*60)
    print(f"1. Open this URL in your browser:\n   {login_url}")
    print(f"2. Login to Zerodha")
    print(f"3. You will be redirected to http://localhost:{CALLBACK_PORT}{CALLBACK_PATH}")
    print("="*60 + "\n")

    # Try to open browser automatically if possible
    try:
        webbrowser.open(login_url)
    except:
        pass

    # 5. Start Callback Receiver
    request_token = wait_for_callback(CALLBACK_PORT)

    if not request_token:
        logger.error("❌ Failed to capture request_token")
        sys.exit(1)

    logger.info("Callback received. Exchanging token...")

    # 6. Exchange & Persist Token
    try:
        access_token = auth.exchange_request_token(request_token)
        auth.persist_access_token(access_token)
        logger.info("✅ Token exchanged and stored securely.")

        # Verify
        if auth.is_session_valid():
            logger.info("✅ Session verification successful.")
        else:
            logger.error("❌ Session verification failed after exchange.")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Error during token exchange: {e}")
        sys.exit(1)

    # 7. Restart/Reload Runner (Optional - depending on how the app runs)
    # Since this is a bootstrap script running before the app, just exiting 0 is enough.
    # The calling scheduler/script will then start the main app.

    logger.info("Auth sequence complete.")

if __name__ == "__main__":
    main()
