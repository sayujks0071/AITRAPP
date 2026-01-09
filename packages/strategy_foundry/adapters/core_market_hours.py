from datetime import datetime, time, timedelta
import pytz
from typing import Optional

# Try to import from core, fallback if fails
try:
    from packages.core.market_hours import MarketHoursGuard
    from packages.core.nse_holidays import get_trading_holidays
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False
    MarketHoursGuard = None

IST = pytz.timezone("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)

class FoundryMarketHours:
    def __init__(self):
        self.use_core = CORE_AVAILABLE
        self.guard = MarketHoursGuard() if CORE_AVAILABLE else None

    def is_market_open(self, dt: Optional[datetime] = None) -> bool:
        if dt is None:
            dt = datetime.now(IST)
        else:
            if dt.tzinfo is None:
                dt = IST.localize(dt)
            else:
                dt = dt.astimezone(IST)

        if self.use_core and self.guard:
            try:
                # Core uses 15:20 as close for entries, but we might want 15:30 for general market status
                # However, let's respect the guard's logic if available
                return self.guard.is_market_open(dt)
            except Exception:
                # Fallback if core fails
                pass

        # Fallback Logic
        # 1. Weekend check
        if dt.weekday() >= 5: # Sat=5, Sun=6
            return False

        # 2. Hours check
        t = dt.time()
        if t < MARKET_OPEN or t >= MARKET_CLOSE:
            return False

        # 3. Simple Holiday check (optional, empty for fallback)
        # We assume if core is missing we don't have holiday data

        return True

    def get_market_status_message(self, dt: Optional[datetime] = None) -> str:
        open_status = self.is_market_open(dt)
        return "OPEN" if open_status else "CLOSED"
