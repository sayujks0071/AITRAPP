#!/usr/bin/env python3
"""
Kite Daily Auth Assistant
Runs daily to ensure a valid Kite Connect session exists.
"""
import http.server
import socketserver
import urllib.parse
import webbrowser
import threading
import time
import os
import sys
import structlog
from packages.core.auth.kite_auth import KiteAuth
from packages.core.config import settings, AppMode

# Configure basic logging for script
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()

# Callback configuration
PORT = int(os.environ.get("AUTH_CALLBACK_PORT", 8080))
CALLBACK_PATH = "/callback"

class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    """Handles the callback from Kite Connect"""

    def log_message(self, format, *args):
        # Suppress default HTTP logging
        pass

    def do_GET(self):
        """Handle GET request with request_token"""
        if self.path.startswith(CALLBACK_PATH):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)

            if 'request_token' in params:
                request_token = params['request_token'][0]
                self.server.request_token = request_token

                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Auth Success!</h1><p>You can close this window.</p></body></html>")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing request_token")
        else:
            self.send_response(404)
            self.end_headers()

def run_auth_flow():
    """Runs the interactive auth flow"""
    auth = KiteAuth()

    # 1. Check if session is already valid
    logger.info("Checking session validity...")
    if auth.is_session_valid():
        logger.info("Session is already valid. No action needed.")
        return 0

    # 2. Safety Check: Default to PAPER mode unless explicit
    if os.environ.get("TRADING_MODE") == "live":
        logger.warning("Running in LIVE mode")
    else:
        logger.info("Running in PAPER mode (default)")

    # 3. Start local callback server
    logger.info(f"Starting callback server on port {PORT}...")

    # Using TCPServer directly to allow easy shutdown
    with socketserver.TCPServer(("", PORT), CallbackHandler) as httpd:
        httpd.request_token = None

        # Start server in a separate thread
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        # 4. Generate and print login URL
        login_url = auth.get_login_url()
        # Ensure redirect_uri matches our local server
        # Note: The redirect_uri is set in the Kite Connect App settings console,
        # but we can't change it here. It must match http://localhost:8080/callback

        logger.info("Auth required!")
        print("\n" + "="*60)
        print("ACTION REQUIRED: Please login to generate a new session")
        print(f"Login URL: {login_url}")
        print("="*60 + "\n")

        # Try to open browser automatically
        try:
            webbrowser.open(login_url)
        except:
            pass

        # 5. Wait for callback
        logger.info("Waiting for callback...")
        start_time = time.time()
        timeout = 300 # 5 minutes timeout

        while httpd.request_token is None:
            if time.time() - start_time > timeout:
                logger.error("Timeout waiting for callback")
                httpd.shutdown()
                return 1
            time.sleep(1)

        request_token = httpd.request_token
        logger.info("Callback received!")
        httpd.shutdown()

        # 6. Exchange and persist token
        try:
            access_token = auth.exchange_request_token(request_token)
            auth.persist_access_token(access_token)
            logger.info("Token exchanged and persisted successfully")
            print("\n✅ Auth setup complete. Application is ready.")
            return 0
        except Exception as e:
            logger.error("Failed to complete auth flow", error=str(e))
            return 1

if __name__ == "__main__":
    sys.exit(run_auth_flow())
