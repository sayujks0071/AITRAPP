"""
Market hours adapter.
Wraps packages.core.market_hours with a fallback if needed.
"""
from datetime import datetime, time
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

# Try to import from core
try:
    from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE
    from packages.core.nse_holidays import get_trading_holidays
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False
    MARKET_OPEN = time(9, 15)
    MARKET_CLOSE = time(15, 20)

class MarketHoursAdapter:
    def __init__(self):
        if CORE_AVAILABLE:
            self.guard = MarketHoursGuard()
        else:
            self.guard = None
            logger.warning("Core market hours not available, using fallback")

    def is_market_open(self, dt: Optional[datetime] = None) -> bool:
        if self.guard:
            return self.guard.is_market_open(dt)

        # Fallback logic
        if dt is None:
            dt = datetime.now()

        # Simple weekday + time check (ignoring holidays in fallback for now)
        if dt.weekday() >= 5:
            return False

        t = dt.time()
        return MARKET_OPEN <= t < MARKET_CLOSE

    def get_holidays(self):
        if CORE_AVAILABLE:
            return get_trading_holidays()
        return []
