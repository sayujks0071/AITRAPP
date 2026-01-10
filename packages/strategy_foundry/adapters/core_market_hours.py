"""Adapter for Core Market Hours"""
import datetime
from typing import Optional
import pytz

# Try importing core, fallback if missing (unlikely in monorepo)
try:
    from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE
    from packages.core.nse_holidays import get_trading_holidays
    _HAS_CORE = True
except ImportError:
    _HAS_CORE = False

IST = pytz.timezone("Asia/Kolkata")

class MarketHoursAdapter:
    """
    Adapter for market hours logic.
    Priority: Core Logic -> Local Fallback
    """

    def __init__(self):
        if _HAS_CORE:
            self.guard = MarketHoursGuard()
        else:
            self.guard = None

    def is_market_open(self, dt: Optional[datetime.datetime] = None) -> bool:
        if dt is None:
            dt = datetime.datetime.now(IST)

        if _HAS_CORE:
            return self.guard.is_market_open(dt)

        # Fallback Logic
        # Weekends
        if dt.weekday() >= 5:
            return False

        # Hours 09:15 - 15:30
        current_time = dt.time()
        start = datetime.time(9, 15)
        end = datetime.time(15, 30)

        if current_time < start or current_time >= end:
            return False

        return True

    def get_trading_holidays(self):
        if _HAS_CORE:
            return get_trading_holidays()
        return []
