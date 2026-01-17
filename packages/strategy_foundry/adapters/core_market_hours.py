from datetime import datetime, time, date
from typing import List
import pytz
from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE, HARD_CLOSE, IST

# Re-export constants
MARKET_OPEN = MARKET_OPEN
MARKET_CLOSE = MARKET_CLOSE
HARD_CLOSE = HARD_CLOSE
IST = IST

class FoundryMarketHours(MarketHoursGuard):
    """
    Adapter for MarketHoursGuard with Foundry specific needs if any.
    Currently just wraps the core class.
    """
    def __init__(self, trading_holidays: List[str] = None):
        super().__init__(trading_holidays)

    def get_market_hours(self):
        return {
            "open": MARKET_OPEN,
            "close": MARKET_CLOSE,
            "hard_close": HARD_CLOSE,
            "timezone": "Asia/Kolkata"
        }
