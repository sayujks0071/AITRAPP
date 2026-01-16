"""Adapter for Core Market Hours"""
from datetime import datetime
import pytz

try:
    from packages.core.market_hours import MarketHoursGuard as CoreGuard
    # Ensure it's available
    _ = CoreGuard
except ImportError:
    CoreGuard = None

IST = pytz.timezone("Asia/Kolkata")

class MarketHoursAdapter:
    def __init__(self):
        if CoreGuard:
            self.core = CoreGuard()
        else:
            self.core = None

    def is_market_open(self, dt: datetime = None) -> bool:
        if self.core:
            return self.core.is_market_open(dt)

        # Fallback
        if dt is None:
            dt = datetime.now(IST)
        if dt.tzinfo is None:
            dt = IST.localize(dt)
        else:
            dt = dt.astimezone(IST)

        # Simple Mon-Fri 09:15-15:30
        if dt.weekday() >= 5: return False

        t = dt.time()
        start = datetime.strptime("09:15", "%H:%M").time()
        end = datetime.strptime("15:30", "%H:%M").time()

        return start <= t <= end
