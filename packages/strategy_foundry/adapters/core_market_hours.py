from typing import Optional
from datetime import datetime
import structlog
from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE

logger = structlog.get_logger(__name__)

class MarketHoursAdapter:
    def __init__(self):
        self.guard = MarketHoursGuard()

    def is_market_open(self, dt: Optional[datetime] = None) -> bool:
        return self.guard.is_market_open(dt)

    def can_trade(self, dt: Optional[datetime] = None) -> bool:
        return self.guard.is_market_open(dt)

    def get_market_hours(self):
        return MARKET_OPEN, MARKET_CLOSE
