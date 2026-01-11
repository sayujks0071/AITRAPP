from packages.core.market_hours import MarketHoursGuard as CoreMarketHoursGuard
from datetime import datetime
import pytz

class MarketHoursGuard(CoreMarketHoursGuard):
    """
    Adapter for Core Market Hours.
    """
    def __init__(self):
        super().__init__()

    def is_market_open(self, dt: datetime = None) -> bool:
        return super().is_market_open(dt)
