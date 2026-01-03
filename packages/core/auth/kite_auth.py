"""Kite Authentication Module"""
import datetime
import os
import structlog
from typing import Optional, Dict
from kiteconnect import KiteConnect, exceptions
from dotenv import set_key

from packages.core.config import settings

logger = structlog.get_logger(__name__)

class KiteAuth:
    """Handles Zerodha Kite authentication flow"""

    def __init__(self):
        self.api_key = settings.kite_api_key
        self.api_secret = settings.kite_api_secret
        self.access_token = settings.kite_access_token
        self.kite = KiteConnect(api_key=self.api_key)

        if self.access_token:
            self.kite.set_access_token(self.access_token)

    def get_login_url(self) -> str:
        """Generate login URL for manual authentication"""
        return self.kite.login_url()

    def is_session_valid(self) -> bool:
        """Check if current session/token is valid by making a lightweight API call"""
        if not self.access_token:
            return False

        try:
            # profile() is lightweight
            self.kite.profile()
            return True
        except exceptions.TokenException:
            logger.warning("Token expired or invalid")
            return False
        except Exception as e:
            # Network errors etc shouldn't invalidate token immediately,
            # but for safety we might treat as invalid or retry.
            # Here we assume if it fails it might be network or invalid.
            # But specific TokenException is the sure sign of expiry.
            if "token" in str(e).lower() or "unauthorized" in str(e).lower():
                return False
            logger.error(f"Error checking session validity: {e}")
            # If it's a network error, we don't know if token is valid.
            # Assuming valid to avoid unnecessary re-login on flaky network,
            # unless we want to be strict.
            # However, the prompt asks to detect missing/expired token.
            return False

    def exchange_request_token(self, request_token: str) -> Optional[str]:
        """Exchange request token for access token"""
        try:
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            access_token = data["access_token"]
            return access_token
        except Exception as e:
            logger.error(f"Failed to exchange request token: {e}")
            raise

    def persist_access_token(self, access_token: str) -> None:
        """Save access token to .env file securely"""
        try:
            env_file = ".env"
            # Update the current instance
            self.access_token = access_token
            self.kite.set_access_token(access_token)

            # Persist to .env
            set_key(env_file, "KITE_ACCESS_TOKEN", access_token)

            # Also update settings singleton if possible, though it's Pydantic
            # settings.kite_access_token = access_token
            # (Pydantic BaseSettings are mutable by default but better to rely on env reload)

            logger.info("Access token persisted successfully")
        except Exception as e:
            logger.error(f"Failed to persist access token: {e}")
            raise
