"""Adapter for core market hours"""
from datetime import datetime, time
import pytz
from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE, HARD_CLOSE

IST = pytz.timezone("Asia/Kolkata")

class FoundryMarketHours:
    def __init__(self):
        self.guard = MarketHoursGuard()

    def is_market_open(self, dt: datetime = None) -> bool:
        return self.guard.is_market_open(dt)

    def get_session_times(self) -> tuple[time, time, time]:
        return MARKET_OPEN, MARKET_CLOSE, HARD_CLOSE
