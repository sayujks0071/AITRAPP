from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE, HARD_CLOSE, IST
from datetime import datetime, time

class MarketSchedule:
    def __init__(self):
        self.guard = MarketHoursGuard()

    def is_open_now(self):
        return self.guard.is_market_open()

    def is_market_hours(self, dt: datetime):
        return self.guard.is_market_open(dt)

    def is_weekend(self, dt: datetime):
        if dt.tzinfo is None:
            dt = IST.localize(dt)
        return dt.weekday() >= 5

    def get_open_time(self):
        return MARKET_OPEN

    def get_close_time(self):
        # Entry close
        return MARKET_CLOSE

    def get_hard_close_time(self):
        return HARD_CLOSE
