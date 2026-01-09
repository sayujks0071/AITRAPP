import os
import logging
from typing import Optional
from kiteconnect import KiteConnect
import dotenv

# Kite Daily Auth Module
# Handles manual login flow, token exchange, and persistence.
# Validates session validity against Kite Connect API.

logger = logging.getLogger(__name__)

class KiteAuth:
    def __init__(self):
        # Support both standard naming and the specific env var from instructions
        self.api_key = os.getenv("KITE_API_KEY") or os.getenv("kiteconnect_api_key")
        self.api_secret = os.getenv("KITE_API_SECRET") or os.getenv("kiteconnect_api_secret")

        # Load access token from environment
        self.access_token = os.getenv("KITE_ACCESS_TOKEN")

        if not self.api_key:
             logger.warning("KITE_API_KEY not found in environment.")

        # Initialize KiteConnect
        # We don't pass access_token immediately if we are going to exchange it,
        # but for session validation we need it.
        self.kite = KiteConnect(api_key=self.api_key, access_token=self.access_token)

    def is_session_valid(self) -> bool:
        """
        Validates current token by calling a lightweight endpoint.
        Returns True if valid, False otherwise.
        """
        if not self.access_token:
            logger.debug("No access token found.")
            return False

        try:
            # profile() is a lightweight call to validate session
            self.kite.profile()
            return True
        except Exception as e:
            # TokenInvalidException or similar implies invalid session
            logger.debug(f"Session validation failed: {str(e)}")
            return False

    def get_login_url(self) -> str:
        """
        Returns the login URL for manual authentication.
        """
        if not self.api_key:
            raise ValueError("API Key is missing")
        return self.kite.login_url()

    def exchange_request_token(self, request_token: str) -> str:
        """
        Exchanges request_token for access_token and persists it.
        Returns the new access_token.
        """
        if not self.api_secret:
            raise ValueError("API Secret is missing")

        try:
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            access_token = data["access_token"]

            # Update instance
            self.access_token = access_token
            self.kite.set_access_token(access_token)

            return access_token
        except Exception as e:
            logger.error(f"Error exchanging request token: {e}")
            raise

    def persist_access_token(self, access_token: str):
        """
        Stores the token securely.
        Prioritizes .env file as per repo convention for 'local encrypted file mechanism'.
        """
        # 1. Update .env file
        env_path = dotenv.find_dotenv()
        if not env_path:
            # Default to .env in current directory if not found
            env_path = ".env"

        logger.info(f"Persisting access token to {env_path}")

        # We use set_key which handles quoting and updates
        dotenv.set_key(env_path, "KITE_ACCESS_TOKEN", access_token)

        # 2. Update current environment to reflect changes immediately in this process
        os.environ["KITE_ACCESS_TOKEN"] = access_token
