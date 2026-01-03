"""Unit test configuration"""
import os
import sys
from unittest.mock import MagicMock

# Set test environment variables before importing any modules
os.environ.setdefault("KITE_API_KEY", "test_api_key")
os.environ.setdefault("KITE_API_SECRET", "test_api_secret")
os.environ.setdefault("KITE_ACCESS_TOKEN", "test_access_token")
os.environ.setdefault("KITE_USER_ID", "test_user_id")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("API_SECRET_KEY", "test_secret_key")
os.environ.setdefault("TRADING_MODE", "paper")
