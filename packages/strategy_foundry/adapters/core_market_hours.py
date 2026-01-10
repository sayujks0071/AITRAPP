"""
Adapter for market hours.
"""
from datetime import datetime
import pytz
from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE, HARD_CLOSE

class MarketHours:
    def __init__(self):
        self.guard = MarketHoursGuard()
        self.tz = pytz.timezone("Asia/Kolkata")

    def is_market_open(self, dt: datetime = None) -> bool:
        return self.guard.is_market_open(dt)

    def get_flatten_time(self) -> str:
        # Return string HH:MM
        return HARD_CLOSE.strftime("%H:%M")

    def get_entry_end_time(self) -> str:
        return MARKET_CLOSE.strftime("%H:%M")
