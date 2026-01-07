import structlog
from datetime import datetime
import pytz

logger = structlog.get_logger(__name__)
IST = pytz.timezone("Asia/Kolkata")

try:
    from packages.core.market_hours import MarketHoursGuard
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False
    logger.warning("packages.core.market_hours not found, using local fallback")

class MarketHoursAdapter:
    def __init__(self):
        if CORE_AVAILABLE:
            self.guard = MarketHoursGuard()
        else:
            self.guard = None

    def is_market_open(self, dt: datetime = None) -> bool:
        if dt is None:
            dt = datetime.now(IST)

        if self.guard:
            return self.guard.is_market_open(dt)

        # Fallback Logic
        if dt.weekday() >= 5: # Sat/Sun
            return False

        t = dt.time()
        # 09:15 to 15:30
        start = datetime.strptime("09:15", "%H:%M").time()
        end = datetime.strptime("15:30", "%H:%M").time()

        return start <= t <= end

    def get_trading_holidays(self):
        if self.guard:
            return list(self.guard.trading_holidays)
        return []
