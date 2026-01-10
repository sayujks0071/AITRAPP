#!/usr/bin/env python3
"""
Kite Daily Auth Assistant (Manual Login + Auto Token Exchange)

Runs daily at 8:00 AM IST.
1. Checks validity of current session.
2. If invalid, triggers login flow:
   - Prints login URL.
   - Wait for manual login via callback (if API server is running).
   - Or if CI, fails/notifies.
"""

import os
import sys
import logging
import argparse
from src.auth.kite_auth import KiteAuth

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Kite Daily Auth Bootstrap")
    parser.add_argument("--check-only", action="store_true", help="Only check session validty, exit 1 if invalid")
    parser.add_argument("--port", type=int, default=8000, help="Port where API server is running (for callback URL info)")
    args = parser.parse_args()

    # Safety Rail: TRADING_MODE default to PAPER
    # This script doesn't trade, but good practice to enforce context
    mode = os.getenv("TRADING_MODE") or os.getenv("APP_MODE") or "PAPER"
    if mode.upper() == "LIVE":
        logger.warning("Running in LIVE mode context.")
    else:
        logger.info("Running in PAPER mode context.")

    auth = KiteAuth()

    # 1. Check if session is valid
    logger.info("Checking Kite session validity...")
    if auth.is_session_valid():
        logger.info("✅ Session is already valid. No action needed.")
        sys.exit(0)

    logger.info("❌ Session is invalid or expired.")

    if args.check_only:
        logger.error("Session invalid and --check-only specified.")
        sys.exit(1)

    # 2. Trigger Login Flow
    try:
        login_url = auth.get_login_url()
        logger.info("=" * 60)
        logger.info(" AUTHENTICATION REQUIRED ")
        logger.info("=" * 60)
        logger.info("Please login manually using the following URL:")
        logger.info(f"\n{login_url}\n")

        # Determine Callback URL for user info
        # We assume the API server is running or will be running on localhost/server
        # The Redirect URI in Kite Console should match this.
        # Assuming standard setup:
        callback_url = f"http://localhost:{args.port}/auth/kite/callback"
        logger.info(f"Ensure your Kite App Redirect URI is set to point to your server's callback endpoint.")
        logger.info(f"e.g., {callback_url} (or your public IP/domain)")
        logger.info("=" * 60)

        # Detect CI environment
        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            logger.warning("Running in CI environment. Cannot perform interactive login.")
            logger.warning("Please manually update the token in GitHub Secrets.")
            # In CI, we just print the URL and exit 1 so the workflow can notify/fail
            sys.exit(1)

        # If running interactively or on VPS
        logger.info("Waiting for you to complete login in the browser...")
        logger.info("Once you login, the callback will be hit on the running API server.")
        logger.info("If the API server is not running, start it: uvicorn apps.api.main:app")

        # We could potentially start a mini-server here if API is not running,
        # but the instructions say "Implement ONE of these". We chose Option A (Backend HTTP route).
        # So we assume the user has the app running or will start it.

    except Exception as e:
        logger.error(f"Error initializing auth flow: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
