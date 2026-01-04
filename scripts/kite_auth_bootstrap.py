#!/usr/bin/env python3
"""
Kite Daily Auth Assistant
Runs daily to ensure a valid Kite Connect session exists.

Features:
- Validates current access token
- Starts local callback server
- Facilitates manual login
- Exchanges request_token for access_token
- Persists tokens to .env securely
- Safety checks (PAPER mode default)
"""

import http.server
import socketserver
import urllib.parse
import webbrowser
import threading
import time
import os
import sys
import re
import datetime
import structlog
from pathlib import Path
from kiteconnect import KiteConnect

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()

# Configuration
# Allow overriding host/port for callback (e.g., if running in Docker/VM)
HOST = os.environ.get("KITE_AUTH_HOST", "127.0.0.1")
PORT = int(os.environ.get("KITE_AUTH_PORT", os.environ.get("AUTH_CALLBACK_PORT", "8080")))
CALLBACK_PATH = "/callback"

class EnvManager:
    """Simple .env reader/updater"""
    def __init__(self, env_path=".env"):
        self.env_path = Path(env_path)
        self.config = {}
        self._load()

    def _load(self):
        """Load .env file into memory"""
        if not self.env_path.exists():
            # Try finding it in root if we are in scripts/
            if Path("../.env").exists():
                self.env_path = Path("../.env")
            elif Path(".env").exists():
                pass
            else:
                logger.warning(".env file not found", path=str(self.env_path))
                return

        try:
            content = self.env_path.read_text()
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, val = line.split('=', 1)
                    self.config[key.strip()] = val.strip()
        except Exception as e:
            logger.error("Failed to load .env", error=str(e))

    def get(self, key, default=None):
        return self.config.get(key, os.environ.get(key, default))

    def update(self, updates: dict):
        """Update multiple keys in .env file preserving comments/structure"""
        if not self.env_path.exists():
            logger.error(".env file not found for update")
            return

        try:
            content = self.env_path.read_text()
            new_content = content

            for key, value in updates.items():
                # Regex to match key=... or key = ...
                pattern = re.compile(fr'^{re.escape(key)}\s*=.*$', re.MULTILINE)
                if pattern.search(new_content):
                    new_content = pattern.sub(f'{key}={value}', new_content)
                else:
                    # Append if not found
                    if not new_content.endswith('\n'):
                        new_content += '\n'
                    new_content += f'{key}={value}\n'

            self.env_path.write_text(new_content)
            logger.info("Updated .env file", keys=list(updates.keys()))

            # Update local config too
            self.config.update(updates)

        except Exception as e:
            logger.error("Failed to update .env", error=str(e))
            raise

class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    """Handles the callback from Kite Connect"""

    def log_message(self, format, *args):
        # Suppress default HTTP logging to avoid leaking tokens in logs
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

def main():
    # 1. Load Configuration
    env = EnvManager()

    api_key = env.get("KITE_API_KEY")
    api_secret = env.get("KITE_API_SECRET")
    access_token = env.get("KITE_ACCESS_TOKEN")

    if not api_key or not api_secret:
        logger.error("Missing KITE_API_KEY or KITE_API_SECRET in .env")
        sys.exit(1)

    # 2. Check Trading Mode
    trading_mode = env.get("TRADING_MODE", "paper").lower()
    app_mode = env.get("APP_MODE", "PAPER").upper()

    if trading_mode == "live" or app_mode == "LIVE":
        logger.warning("⚠️  Running in LIVE mode")
    else:
        logger.info("Running in PAPER mode (default)")

    # 3. Check Session Validity
    kite = KiteConnect(api_key=api_key)

    if access_token:
        kite.set_access_token(access_token)
        try:
            logger.info("Verifying existing session...")
            kite.profile()
            logger.info("✅ Session is valid. No action needed.")
            sys.exit(0)
        except Exception as e:
            logger.warning("Session invalid or expired", error=str(e))
    else:
        logger.info("No access token found")

    # 4. Start Callback Server
    logger.info(f"Starting callback server at http://{HOST}:{PORT}{CALLBACK_PATH}...")

    # Allow address reuse to avoid "Address already in use" errors during quick restarts
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer((HOST, PORT), CallbackHandler) as httpd:
        httpd.request_token = None

        # Start server in thread
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        # 5. Generate Login URL
        login_url = kite.login_url()

        print("\n" + "="*60)
        print("🔓 ACTION REQUIRED: Login to Zerodha")
        print(f"Login URL: {login_url}")
        print("="*60 + "\n")

        # Attempt to open browser
        try:
            webbrowser.open(login_url)
        except:
            pass

        # 6. Wait for Callback
        logger.info("Waiting for callback...")
        start_time = time.time()
        timeout = 300  # 5 minutes

        while httpd.request_token is None:
            if time.time() - start_time > timeout:
                logger.error("Timeout waiting for login")
                httpd.shutdown()
                sys.exit(1)
            time.sleep(1)

        request_token = httpd.request_token
        logger.info("Callback received")
        httpd.shutdown()

        # 7. Exchange Token
        try:
            logger.info("Exchanging request token...")
            data = kite.generate_session(request_token, api_secret=api_secret)

            new_access_token = data["access_token"]
            user_id = data.get("user_id", "")
            # ISO timestamp for when token was created (now)
            created_at = datetime.datetime.now().isoformat()

            # 8. Persist to .env
            env.update({
                "KITE_ACCESS_TOKEN": new_access_token,
                "KITE_USER_ID": user_id,
                "KITE_TOKEN_CREATED_AT_ISO": created_at
            })

            logger.info("✅ Auth setup complete. Tokens persisted.")
            sys.exit(0)

        except Exception as e:
            logger.error("Failed to exchange token", error=str(e))
            sys.exit(1)

if __name__ == "__main__":
    main()
