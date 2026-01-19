"""
Adapter for market hours and holidays.
"""
from datetime import datetime
from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE
from packages.core.nse_holidays import get_trading_holidays

class MarketHoursAdapter:
    def __init__(self):
        self.guard = MarketHoursGuard()

    def is_market_open(self, dt: datetime = None) -> bool:
        return self.guard.is_market_open(dt)

    def get_trading_holidays(self):
        return get_trading_holidays()

    @property
    def market_open_time(self):
        return MARKET_OPEN

    @property
    def market_close_time(self):
        return MARKET_CLOSE
