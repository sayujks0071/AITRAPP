"""Adapter for core market hours to strategy foundry"""
from datetime import datetime, time
import pytz
from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE, HARD_CLOSE
from packages.core.nse_holidays import get_trading_holidays

IST = pytz.timezone("Asia/Kolkata")

class MarketHoursAdapter:
    """Adapts core MarketHoursGuard for foundry usage"""

    def __init__(self):
        try:
            self.guard = MarketHoursGuard()
        except Exception:
            # Fallback if core fails (e.g. holiday fetch issues)
            self.guard = MarketHoursGuard(trading_holidays=[])

    def is_market_open(self, dt: datetime = None) -> bool:
        return self.guard.is_market_open(dt)

    def is_trading_session(self, dt: datetime) -> bool:
        """Strict check for valid trading session (including intraday boundaries)"""
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = IST.localize(dt)
        else:
            dt = dt.astimezone(IST)

        # Basic checks from core
        if not self.guard.can_place_exit(dt): # Use exit window as max bound
            return False

        return True

    def get_session_close(self) -> time:
        return HARD_CLOSE

    def get_session_open(self) -> time:
        return MARKET_OPEN
