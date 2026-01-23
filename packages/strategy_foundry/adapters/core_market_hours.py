# StrategyFoundry Implementation
from datetime import datetime, time
import pytz
from typing import Optional
from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE, HARD_CLOSE

class MarketHoursAdapter:
    """
    Adapter for market hours logic.
    """
    def __init__(self):
        self.guard = MarketHoursGuard()
        self.timezone = pytz.timezone("Asia/Kolkata")

    def is_market_open(self, dt: Optional[datetime] = None) -> bool:
        return self.guard.is_market_open(dt)

    def is_session_closing(self, dt: datetime, buffer_minutes: int = 5) -> bool:
        """
        Check if we are within buffer_minutes of HARD_CLOSE.
        """
        if dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        else:
            dt = dt.astimezone(self.timezone)

        # Naive time comparison
        current_time = dt.time()

        # Construct close time for today
        close_dt = dt.replace(hour=HARD_CLOSE.hour, minute=HARD_CLOSE.minute, second=0, microsecond=0)

        # If current time is after close, yes
        if current_time >= HARD_CLOSE:
            return True

        # Check difference
        diff = (close_dt - dt).total_seconds() / 60.0
        return diff <= buffer_minutes
