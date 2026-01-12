#!/usr/bin/env python3
"""
Kite Auth Bootstrap Script

Daily 8:00 AM job to ensure valid Kite Connect session.
- Checks if current session is valid.
- If invalid, starts a local server to capture the callback.
- Prints login URL for manual login.
- Exchanges request_token for access_token and persists it.

Usage:
  python scripts/kite_auth_bootstrap.py [--check-only] [--port PORT]
"""

import sys
import os
import argparse
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time

# Ensure src is in python path
sys.path.insert(0, os.getcwd())

from src.auth.kite_auth import KiteAuth
from packages.core.config import AppMode

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("kite_auth_bootstrap")

# Global variable to store captured token
captured_request_token = None
server_stop_event = threading.Event()

class CallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default server logs
        pass

    def do_GET(self):
        global captured_request_token
        parsed_path = urlparse(self.path)

        # Check if this is the callback
        # We accept root / or /auth/kite/callback or anything really, as long as it has request_token
        query_components = parse_qs(parsed_path.query)

        if "request_token" in query_components:
            captured_request_token = query_components["request_token"][0]

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <head><title>Auth Success</title></head>
                <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                    <h1 style="color: green;">Authentication Captured</h1>
                    <p>You can close this window now.</p>
                </body>
                </html>
            """)

            # Signal server to stop
            threading.Thread(target=self.server.shutdown).start()
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Missing request_token</h1>")

def start_server(port):
    server_address = ('', port)
    httpd = HTTPServer(server_address, CallbackHandler)
    logger.info(f"Local callback server listening on port {port}")
    httpd.serve_forever()

def main():
    parser = argparse.ArgumentParser(description="Kite Auth Bootstrap")
    parser.add_argument("--check-only", action="store_true", help="Only check session validity, do not prompt login")
    parser.add_argument("--port", type=int, default=8000, help="Port for local callback server")
    args = parser.parse_args()

    # Safety Rail: Default to PAPER if not set or if invalid
    # Support both TRADING_MODE (requested) and APP_MODE (internal config)
    trading_mode_env = os.environ.get("TRADING_MODE")
    app_mode_env = os.environ.get("APP_MODE")

    if trading_mode_env:
        # Normalize TRADING_MODE to APP_MODE
        if trading_mode_env.lower() == "live":
            os.environ["APP_MODE"] = "LIVE"
        else:
            os.environ["APP_MODE"] = "PAPER"
    elif not app_mode_env:
        # Default to PAPER if neither is set
        logger.info("TRADING_MODE/APP_MODE not set, defaulting to PAPER")
        os.environ["APP_MODE"] = "PAPER"

    # Re-read confirmed mode
    app_mode = os.environ.get("APP_MODE", "PAPER")
    if app_mode == "LIVE":
        logger.warning("⚠️  RUNNING IN LIVE MODE ⚠️")
    else:
        logger.info(f"Running in {app_mode} mode")

    auth = KiteAuth()

    logger.info("Checking session validity...")
    if auth.is_session_valid():
        logger.info("✅ Session is already valid.")
        sys.exit(0)

    logger.info("❌ Session is invalid or expired.")

    if args.check_only:
        logger.error("Session invalid and --check-only specified. Exiting.")
        sys.exit(1)

    # Manual Login Flow
    login_url = auth.get_login_url()

    # We assume the user has configured the redirect_uri to http://localhost:PORT/auth/kite/callback
    # or similar. The script listens on all paths.

    logger.info("-" * 60)
    logger.info("ACTION REQUIRED: Please login manually.")
    logger.info(f"Login URL: {login_url}")
    logger.info(f"Callback Receiver: http://localhost:{args.port}/")
    logger.info("-" * 60)

    # Start server in a separate thread
    server_thread = threading.Thread(target=start_server, args=(args.port,))
    server_thread.start()

    logger.info("Waiting for callback...")

    # Wait for server thread to finish (it shuts down upon receiving token)
    server_thread.join()

    if captured_request_token:
        logger.info("Callback received. Exchanging token...")
        try:
            access_token = auth.exchange_request_token(captured_request_token)
            auth.persist_access_token(access_token)
            logger.info("✅ Token exchanged and persisted successfully.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Failed to exchange token: {e}")
            sys.exit(1)
    else:
        logger.error("Server stopped without capturing token.")
        sys.exit(1)

if __name__ == "__main__":
    main()
