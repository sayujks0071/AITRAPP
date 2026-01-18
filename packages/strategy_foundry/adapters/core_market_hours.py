from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE
from datetime import datetime, time
import pytz

# IST Timezone
IST = pytz.timezone("Asia/Kolkata")

class MarketHoursAdapter:
    def __init__(self):
        self.guard = MarketHoursGuard()

    def is_market_open(self, dt: datetime = None) -> bool:
        return self.guard.is_market_open(dt)

    def get_market_hours(self):
        return MARKET_OPEN, MARKET_CLOSE
