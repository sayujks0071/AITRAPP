"""Script to bootstrap Kite authentication daily"""
import os
import sys
import time
import structlog
import http.server
import socketserver
import urllib.parse
from typing import Optional
from pathlib import Path
import re

# Add repo root to path
sys.path.append(os.getcwd())

from src.auth.kite_auth import KiteAuth
from packages.core.config import settings, AppMode

logger = structlog.get_logger(__name__)

# Constants
PORT = 8080
CALLBACK_PATH = "/callback"

class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    """Handles the redirect callback from Kite Connect"""

    def log_message(self, format, *args):
        # Suppress default logging to keep console clean
        pass

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path == CALLBACK_PATH:
            query_params = urllib.parse.parse_qs(parsed_url.query)

            if "request_token" in query_params:
                request_token = query_params["request_token"][0]
                self.server.request_token = request_token

                # Send success response
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Auth Success!</h1><p>You can close this window and return to the terminal.</p>")
            else:
                self.send_error(400, "Missing request_token")
        else:
            self.send_error(404, "Not Found")

class KiteAuthBootstrap:
    def __init__(self):
        self.auth = KiteAuth()

    def update_env_file(self, access_token: str, user_id: str):
        """Updates the .env file with new credentials"""
        env_path = Path(".env")
        if not env_path.exists():
            logger.error(".env file not found")
            return

        try:
            content = env_path.read_text()

            # Securely replace token
            if "KITE_ACCESS_TOKEN=" in content:
                content = re.sub(
                    r'KITE_ACCESS_TOKEN=.*',
                    f'KITE_ACCESS_TOKEN={access_token}',
                    content
                )
            else:
                content += f"\nKITE_ACCESS_TOKEN={access_token}"

            if "KITE_USER_ID=" in content:
                content = re.sub(
                    r'KITE_USER_ID=.*',
                    f'KITE_USER_ID={user_id}',
                    content
                )
            else:
                content += f"\nKITE_USER_ID={user_id}"

            env_path.write_text(content)
            logger.info("Updated .env with new credentials")

        except Exception as e:
            logger.error("Failed to update .env file", error=str(e))
            raise

    def run_callback_server(self) -> str:
        """Starts a local server to capture the request token"""
        with socketserver.TCPServer(("localhost", PORT), CallbackHandler) as httpd:
            # Allow reuse address to avoid port conflicts
            httpd.allow_reuse_address = True
            httpd.request_token = None

            login_url = self.auth.get_login_url()
            print("\n" + "="*60)
            print(f"⚠️  AUTHENTICATION REQUIRED")
            print("="*60)
            print(f"\n1. Open this URL in your browser:\n")
            print(f"   {login_url}")
            print(f"\n2. Login to Zerodha")
            print(f"3. Wait for the success message")
            print("\nWaiting for callback on port 8080...")

            while not httpd.request_token:
                httpd.handle_request()

            return httpd.request_token

    def execute(self):
        """Main execution flow"""
        # 1. Safety Check: Ensure we don't accidentally run in LIVE mode without explicit intent
        # Although this script prepares for live/paper, the script itself is safe.
        # But we enforce paper default in env if not set.
        if settings.app_mode == AppMode.LIVE and not os.getenv("I_UNDERSTAND_LIVE_TRADING"):
             logger.warning("Running in LIVE mode but I_UNDERSTAND_LIVE_TRADING is not set. Proceeding with caution.")

        # 2. Check validity
        if self.auth.is_session_valid():
            logger.info("Session is already valid. No action needed.")
            return

        # 3. Start Callback Server & Get Token
        try:
            request_token = self.run_callback_server()
            logger.info("Callback received", request_token="***") # masked

            # 4. Exchange Token
            session_data = self.auth.exchange_request_token(request_token)
            access_token = session_data["access_token"]
            user_id = session_data["user_id"]

            # 5. Persist
            self.update_env_file(access_token, user_id)

            logger.info("Authentication completed successfully")

        except Exception as e:
            logger.error("Authentication failed", error=str(e))
            sys.exit(1)

if __name__ == "__main__":
    bootstrap = KiteAuthBootstrap()
    bootstrap.execute()
