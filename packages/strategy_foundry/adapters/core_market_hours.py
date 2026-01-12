import pandas as pd
from datetime import datetime, time, timedelta
import pytz
from typing import Optional

# Adapter to wrap core market hours
# If core fails or is missing, use local fallback

def is_market_open(timestamp: datetime = None) -> bool:
    """
    Check if market is open.
    Uses core logic if available, else fallback.
    """
    try:
        from packages.core.market_hours import MarketHoursGuard
        guard = MarketHoursGuard()
        return guard.is_market_open(timestamp)
    except Exception as e:
        # print(f"Core market hours failed: {e}. Using fallback.")
        pass

    # Fallback Logic
    # 09:15 - 15:30 IST
    ist = pytz.timezone("Asia/Kolkata")

    if timestamp is None:
        timestamp = datetime.now(ist)
    else:
        # Convert to IST if aware, else assume UTC? Or assume local?
        # Safe to assume UTC if no tzinfo, or ensure input is aware.
        if timestamp.tzinfo is None:
             # Assume UTC if naive, as is common in servers
             timestamp = pytz.utc.localize(timestamp)
        timestamp = timestamp.astimezone(ist)

    if timestamp.weekday() >= 5: # Sat, Sun
        return False

    t = timestamp.time()
    start = time(9, 15)
    end = time(15, 30)

    if start <= t <= end:
        return True
    return False

def is_trading_day(date_obj: datetime.date) -> bool:
    """
    Check if a specific date is a trading day (not weekend, not holiday).
    """
    if date_obj.weekday() >= 5:
        return False

    try:
        from packages.core.market_hours import MarketHoursGuard
        guard = MarketHoursGuard()
        return date_obj.isoformat() not in guard.trading_holidays
    except Exception:
        # Fallback: just check weekend
        return True
