from packages.core.market_hours import MarketHoursGuard, IST
from packages.core.nse_holidays import get_trading_holidays

class MarketHoursAdapter:
    """Adapter for core market hours and holidays"""

    def __init__(self):
        self.guard = MarketHoursGuard()

    def is_market_open(self, dt=None) -> bool:
        """Check if market is open for trading"""
        return self.guard.is_market_open(dt)

    def is_holiday(self, date_str: str) -> bool:
        """Check if a date string (YYYY-MM-DD) is a holiday"""
        return date_str in self.guard.trading_holidays

    def get_timezone(self):
        """Get the market timezone"""
        return IST
