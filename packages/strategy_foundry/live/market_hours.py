"""
Market hours check for live publishing.
"""
from datetime import datetime
import pytz
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter

class LiveMarketHours:
    def __init__(self):
        self.adapter = MarketHoursAdapter()
        self.tz = pytz.timezone("Asia/Kolkata")

    def is_market_open(self) -> bool:
        """
        Check if market is currently open for trading.
        """
        now = datetime.now(self.tz)
        return self.adapter.is_market_open(now)

    def get_current_time_ist(self) -> str:
        return datetime.now(self.tz).isoformat()
