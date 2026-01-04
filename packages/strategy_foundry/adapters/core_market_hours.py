from datetime import datetime, time
import pytz
from typing import Optional

# Try to import core logic, fallback if not available
try:
    from packages.core.market_hours import is_market_open as core_is_market_open
except ImportError:
    core_is_market_open = None

def is_market_open(timestamp: Optional[datetime] = None) -> bool:
    """
    Check if market is open (NSE Equity/Derivatives hours).
    Default: Mon-Fri 09:15 - 15:30 IST.
    """
    if core_is_market_open:
        try:
            return core_is_market_open(timestamp)
        except:
            pass

    # Fallback Logic
    tz = pytz.timezone("Asia/Kolkata")
    if timestamp is None:
        now = datetime.now(tz)
    else:
        now = timestamp.astimezone(tz)

    # Check Weekend
    if now.weekday() >= 5: # Sat=5, Sun=6
        return False

    # Check Time
    current_time = now.time()
    market_start = time(9, 15)
    market_end = time(15, 30)

    return market_start <= current_time <= market_end
