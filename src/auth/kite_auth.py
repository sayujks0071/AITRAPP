"""
Kite Authentication Module

This module handles Zerodha Kite Connect authentication, including:
- Session validity checking
- Login URL generation
- Token exchange
- Access token persistence to .env
"""
import os
import logging
from typing import Optional
from kiteconnect import KiteConnect
import dotenv

logger = logging.getLogger(__name__)

class KiteAuth:
    """
    Handles authentication logic for Zerodha Kite Connect.
    """
    def __init__(self):
        # Support both standard naming and the specific env var from instructions
        self.api_key = os.getenv("KITE_API_KEY") or os.getenv("kiteconnect_api_key")
        self.api_secret = os.getenv("KITE_API_SECRET") or os.getenv("kiteconnect_api_secret")

        # Load access token from environment (which might be loaded from .env)
        self.access_token = os.getenv("KITE_ACCESS_TOKEN")

        if not self.api_key or not self.api_secret:
            logger.warning("KITE_API_KEY or KITE_API_SECRET not found in environment. Auth functions will fail.")

        self.kite = KiteConnect(api_key=self.api_key, access_token=self.access_token)

    def is_session_valid(self) -> bool:
        """
        Checks if the current session (access_token) is valid by making a lightweight API call.
        Returns True if valid, False otherwise.
        """
        if not self.access_token:
            return False

        try:
            # Lightweight call to validate session. profile() is a good candidate.
            self.kite.profile()
            return True
        except Exception as e:
            # TokenInvalidException is raised by kiteconnect if token is bad
            # We treat any error as invalid session for safety
            logger.debug(f"Session validation failed: {str(e)}")
            return False

    def get_login_url(self) -> str:
        """Returns the login URL for manual authentication."""
        if not self.api_key:
            raise ValueError("API Key is missing")
        return str(self.kite.login_url())

    def exchange_request_token(self, request_token: str) -> str:
        """
        Exchanges request_token for access_token using the API Secret.
        Updates the internal state and returns the access_token.
        """
        if not self.api_secret:
            raise ValueError("API Secret is missing")

        try:
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            access_token = str(data["access_token"])
            self.kite.set_access_token(access_token)
            self.access_token = access_token
            return access_token
        except Exception as e:
            logger.error(f"Error exchanging request token: {e}")
            raise

    def persist_access_token(self, access_token: str):
        """
        Persists the access token to the .env file and updates current environment variables.
        """
        # Find .env file
        env_path = dotenv.find_dotenv()
        if not env_path:
            # If not found, use .env in current directory
            env_path = ".env"

        logger.info(f"Persisting access token to {env_path}")

        # Use dotenv.set_key to update the file
        # This will create the file if it doesn't exist, and update or add the key
        dotenv.set_key(env_path, "KITE_ACCESS_TOKEN", access_token)

        # Update current process environment
        os.environ["KITE_ACCESS_TOKEN"] = access_token
