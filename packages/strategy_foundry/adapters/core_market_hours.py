from datetime import datetime
from packages.core.market_hours import MarketHoursGuard, IST
from packages.core.nse_holidays import get_trading_holidays

class MarketHoursAdapter:
    """Adapter for Market Hours logic"""

    def __init__(self):
        self.guard = MarketHoursGuard()
        self.holidays = get_trading_holidays()

    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        return self.guard.is_market_open()

    def get_holidays(self) -> set:
        return self.holidays

    def is_holiday(self, date_obj) -> bool:
        date_str = date_obj.strftime("%Y-%m-%d")
        return date_str in self.holidays
