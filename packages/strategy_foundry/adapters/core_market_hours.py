"""
Adapter for core market hours.
"""
from datetime import datetime
from packages.core.market_hours import MarketHoursGuard

class MarketHoursAdapter:
    def __init__(self):
        self.guard = MarketHoursGuard()

    def is_market_open(self, dt: datetime = None) -> bool:
        return self.guard.is_market_open(dt)

    def can_place_entry(self, dt: datetime = None) -> bool:
        return self.guard.can_place_entry(dt)
