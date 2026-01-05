#!/usr/bin/env python3
import http.server
import urllib.parse
import sys
import os
import logging
import threading
import time

# Ensure we can import from src
sys.path.append(os.getcwd())

from src.auth.kite_auth import KiteAuth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("KiteAuthBootstrap")

PORT = 8080
CALLBACK_PATH = "/callback"

class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default logging to keep output clean
        pass

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path == CALLBACK_PATH:
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if 'request_token' in query_params:
                self.server.request_token = query_params['request_token'][0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"<h1>Auth Success!</h1><p>Token received. You can close this window.</p>")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"<h1>Error</h1><p>No request_token found in URL.</p>")
        else:
            self.send_response(404)
            self.end_headers()

def main():
    logger.info("Starting Kite Daily Auth Assistant...")

    # 4) Add safety rails: Ensure TRADING_MODE defaults to paper
    trading_mode = os.getenv("TRADING_MODE", "PAPER").upper()
    if trading_mode == "LIVE":
        logger.warning("⚠️  WARNING: TRADING_MODE is set to LIVE. Be careful!")
    else:
        logger.info(f"Running in {trading_mode} mode.")

    try:
        auth = KiteAuth()
    except Exception as e:
        logger.error(f"Failed to initialize KiteAuth: {e}")
        # If API keys are missing, we can't proceed
        sys.exit(1)

    logger.info("Checking session validity...")
    if auth.is_session_valid():
        logger.info("✅ Session is valid. No action required.")
        sys.exit(0)

    logger.info("❌ Session invalid or expired. Starting manual login flow.")

    try:
        login_url = auth.get_login_url()
    except Exception as e:
        logger.error(f"Failed to generate login URL: {e}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info(f"👉 Please login here: {login_url}")
    logger.info("=" * 60)

    # Start server to listen for callback
    server = http.server.HTTPServer(('localhost', PORT), CallbackHandler)
    server.request_token = None

    logger.info(f"Listening for callback on http://localhost:{PORT}{CALLBACK_PATH}")
    logger.info("Waiting for redirect...")

    try:
        # Loop until we get the token
        while server.request_token is None:
            server.handle_request()

        request_token = server.request_token
        logger.info("Callback received!")

        logger.info("Exchanging request_token for access_token...")
        access_token = auth.exchange_request_token(request_token)

        logger.info("Persisting access token...")
        auth.persist_access_token(access_token)

        logger.info("✅ Token stored successfully.")
        logger.info("🔄 Please restart your trading application if it is running to pick up the new token.")

    except KeyboardInterrupt:
        logger.info("\nBootstrap interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during auth flow: {e}")
        sys.exit(1)
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
