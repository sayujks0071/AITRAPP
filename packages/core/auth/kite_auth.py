import os
import re
from pathlib import Path
from typing import Optional
import structlog
from kiteconnect import KiteConnect
from packages.core.config import settings

logger = structlog.get_logger(__name__)

class KiteAuth:
    """
    Handles Zerodha Kite authentication, token exchange, and persistence.
    Designed for daily manual login flow.
    """
    def __init__(self):
        self.api_key = settings.kite_api_key
        self.api_secret = settings.kite_api_secret
        self.access_token = settings.kite_access_token

    def _get_client(self, access_token: Optional[str] = None) -> KiteConnect:
        """Returns a configured KiteConnect instance."""
        kite = KiteConnect(api_key=self.api_key)
        if access_token:
            kite.set_access_token(access_token)
        elif self.access_token:
            kite.set_access_token(self.access_token)
        return kite

    def is_session_valid(self) -> bool:
        """
        Checks if the current session (access_token) is valid by making a lightweight API call.
        """
        if not self.access_token:
            return False

        try:
            kite = self._get_client()
            # profile() is a lightweight call to verify session
            kite.profile()
            return True
        except Exception as e:
            # Any error (TokenException, NetworkException, etc.) implies invalid or unusable session
            logger.warning("Session invalid or expired", error=str(e))
            return False

    def get_login_url(self) -> str:
        """Generates the official Kite login URL."""
        kite = self._get_client()
        return kite.login_url()

    def exchange_request_token(self, request_token: str) -> str:
        """
        Exchanges the request_token (from login redirect) for an access_token.
        """
        kite = self._get_client()
        try:
            data = kite.generate_session(request_token, api_secret=self.api_secret)
            access_token = data["access_token"]
            return access_token
        except Exception as e:
            logger.error("Failed to exchange request token", error=str(e))
            raise

    def persist_access_token(self, access_token: str) -> None:
        """
        Persists the access_token to the .env file securely.
        Uses the existing local file mechanism as requested.
        """
        # Find .env file in the root directory
        # packages/core/auth/kite_auth.py -> ... -> root
        root_dir = Path(__file__).resolve().parents[3]
        env_file = root_dir / ".env"

        if not env_file.exists():
            # If .env doesn't exist (e.g. CI), maybe try env.example or just log warning
            logger.warning(".env file not found at expected path", path=str(env_file))
            return

        try:
            content = env_file.read_text()

            # Use regex to replace KITE_ACCESS_TOKEN
            # This handles KITE_ACCESS_TOKEN=old_value or KITE_ACCESS_TOKEN=""
            # Handles optional spaces around equal sign
            if re.search(r'^KITE_ACCESS_TOKEN\s*=', content, flags=re.MULTILINE):
                new_content = re.sub(
                    r'^KITE_ACCESS_TOKEN\s*=.*$',
                    f'KITE_ACCESS_TOKEN={access_token}',
                    content,
                    flags=re.MULTILINE
                )
            else:
                # Append if not found
                new_content = content + f"\nKITE_ACCESS_TOKEN={access_token}\n"

            env_file.write_text(new_content)
            logger.info("Access token persisted to .env")

            # Update local instance
            self.access_token = access_token

        except Exception as e:
            logger.error("Failed to persist access token", error=str(e))
            raise
