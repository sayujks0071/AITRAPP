from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE, HARD_CLOSE
import pytz

IST = pytz.timezone("Asia/Kolkata")

class MarketHoursAdapter:
    def __init__(self):
        self.guard = MarketHoursGuard()

    def is_market_open(self):
        return self.guard.is_market_open()

    def get_market_times(self):
        return {
            "open": MARKET_OPEN,
            "close": MARKET_CLOSE,
            "hard_close": HARD_CLOSE
        }
