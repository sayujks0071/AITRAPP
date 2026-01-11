from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE, IST
from datetime import datetime

class MarketHoursAdapter:
    def __init__(self):
        self.guard = MarketHoursGuard()

    def is_market_open(self, dt: datetime = None) -> bool:
        return self.guard.is_market_open(dt)

    def get_timezone(self):
        return IST
