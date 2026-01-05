"""
Market hours adapter.
Reuses packages.core.market_hours if available, else falls back to local logic.
"""
from datetime import datetime, time
import pytz
try:
    from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE
    HAS_CORE = True
except ImportError:
    HAS_CORE = False

IST = pytz.timezone("Asia/Kolkata")

# Fallback constants
FALLBACK_OPEN = time(9, 15)
FALLBACK_CLOSE = time(15, 30)

class MarketHoursAdapter:
    def __init__(self):
        if HAS_CORE:
            self.guard = MarketHoursGuard()
        else:
            self.guard = None

    def is_market_open(self, dt: datetime = None) -> bool:
        if dt is None:
            dt = datetime.now(IST)
        elif dt.tzinfo is None:
            dt = IST.localize(dt)
        else:
            dt = dt.astimezone(IST)

        if HAS_CORE:
            return self.guard.is_market_open(dt)

        # Fallback logic
        if dt.weekday() >= 5: # Weekend
            return False

        current_time = dt.time()
        return FALLBACK_OPEN <= current_time < FALLBACK_CLOSE

    def can_publish_signal(self, dt: datetime = None) -> bool:
        """
        Signals are published during market hours.
        """
        return self.is_market_open(dt)
