"""Kite Authentication Module"""
import structlog
from typing import Optional, Dict, Any
from kiteconnect import KiteConnect
from kiteconnect.exceptions import TokenException, NetworkException
from packages.core.config import settings

logger = structlog.get_logger(__name__)

class KiteAuth:
    """Handles Kite Connect authentication and session management"""

    def __init__(self):
        self.api_key = settings.kite_api_key
        self.api_secret = settings.kite_api_secret
        self.access_token = settings.kite_access_token
        self.user_id = settings.kite_user_id
        self.kite = KiteConnect(api_key=self.api_key)
        self.kite.set_access_token(self.access_token)

    def is_session_valid(self) -> bool:
        """
        Validates the current session by making a lightweight API call.
        Returns True if session is valid, False otherwise.
        """
        if not self.access_token:
            logger.info("No access token found")
            return False

        try:
            # profile() is a lightweight call to check validity
            self.kite.profile()
            logger.info("Session is valid")
            return True
        except (TokenException, NetworkException) as e:
            logger.warning("Session invalid or network error", error=str(e))
            return False
        except Exception as e:
            logger.error("Unexpected error checking session", error=str(e))
            return False

    def get_login_url(self) -> str:
        """Returns the Kite Connect login URL"""
        return self.kite.login_url()

    def exchange_request_token(self, request_token: str) -> Dict[str, Any]:
        """
        Exchanges request_token for access_token.
        Returns the session data.
        """
        try:
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            self.kite.set_access_token(data["access_token"])
            logger.info("Token exchange successful")
            return data
        except Exception as e:
            logger.error("Token exchange failed", error=str(e))
            raise
