"""Kite Authentication Module"""
import os
import structlog
from typing import Optional
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
        except exceptions.NetworkException as e:
            # Network-related errors shouldn't immediately invalidate the token.
            logger.error(f"Network error while checking session validity: {e}")
            # Assume token is still valid to avoid unnecessary re-login on flaky networks.
            return True
        except Exception as e:
            # Unexpected errors: log and conservatively treat session as invalid
            logger.error("Unexpected error checking session validity", exc_info=True)
            return True

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
            # Resolve .env path relative to project root, with optional override
            project_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
            )
            default_env_file = os.path.join(project_root, ".env")
            env_file = os.getenv("ENV_FILE_PATH", default_env_file)
            
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
