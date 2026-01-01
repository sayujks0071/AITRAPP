"""Adapter for Market Hours and Holidays"""
from datetime import datetime, time, date
from typing import Set
import pytz
import logging
from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE
from packages.core.nse_holidays import get_trading_holidays

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

class MarketHoursAdapter:
    def __init__(self):
        try:
            self.guard = MarketHoursGuard()
            self.holidays = self.guard.trading_holidays
        except Exception as e:
            logger.warning(f"Could not initialize core MarketHoursGuard, falling back to local: {e}")
            self.guard = None
            self.holidays = self._get_fallback_holidays()

    def _get_fallback_holidays(self) -> Set[str]:
        # Minimal fallback or fetch fresh
        try:
            return get_trading_holidays()
        except Exception:
            return set()

    def is_market_open(self, dt: datetime = None) -> bool:
        if dt is None:
            dt = datetime.now(IST)

        # Ensure timezone awareness
        if dt.tzinfo is None:
            dt = IST.localize(dt)
        else:
            dt = dt.astimezone(IST)

        if self.guard:
            return self.guard.is_market_open(dt)

        # Fallback Logic
        if dt.date().isoformat() in self.holidays:
            return False

        if dt.weekday() >= 5: # Sat/Sun
            return False

        t = dt.time()
        # Using imported constants if available, else hardcoded
        open_time = MARKET_OPEN
        close_time = MARKET_CLOSE

        return open_time <= t < close_time

    def is_market_open_now(self) -> bool:
        return self.is_market_open()
