from packages.core.market_hours import MarketHoursGuard
from datetime import datetime
import pytz

class MarketAdapter:
    def __init__(self):
        self.guard = MarketHoursGuard()
        self.timezone = pytz.timezone("Asia/Kolkata")

    def is_market_open(self, dt: datetime = None) -> bool:
        return self.guard.is_market_open(dt)

    def is_holiday(self, dt: datetime) -> bool:
        # Check against guard's holiday list
        if dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        date_str = dt.date().isoformat()
        return date_str in self.guard.trading_holidays
