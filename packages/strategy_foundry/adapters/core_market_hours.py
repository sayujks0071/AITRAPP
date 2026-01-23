from datetime import datetime
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import pytz

from packages.core.market_hours import HARD_CLOSE, MARKET_CLOSE, MARKET_OPEN, MarketHoursGuard


class MarketHoursAdapter:
    """
    Adapter for market hours logic.
    """
    def __init__(self):
        self.guard = MarketHoursGuard()
        self.timezone = pytz.timezone("Asia/Kolkata")

    def is_market_open(self, dt: Optional[datetime] = None) -> bool:
        return self.guard.is_market_open(dt)

    def is_session_closing(self, dt: datetime, buffer_minutes: int = 5) -> bool:
        """
        Check if we are within buffer_minutes of HARD_CLOSE.
        """
        if dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        else:
            dt = dt.astimezone(self.timezone)

        # Naive time comparison
        current_time = dt.time()

        # Construct close time for today
        close_dt = dt.replace(hour=HARD_CLOSE.hour, minute=HARD_CLOSE.minute, second=0, microsecond=0)

        # If current time is after close, yes
        if current_time >= HARD_CLOSE:
            return True

        # Check difference
        diff = (close_dt - dt).total_seconds() / 60.0
        return diff <= buffer_minutes

    def get_masks(self, times: pd.DatetimeIndex) -> Tuple[np.ndarray, np.ndarray]:
        """
        Vectorized calculation of market open and session closing masks.
        Returns: (is_market_open_mask, is_session_closing_mask)
        """
        # Ensure timezone is IST
        if times.tz is None:
            times_ist = times.tz_localize(self.timezone)
        else:
            times_ist = times.tz_convert(self.timezone)

        # 1. Market Open Mask
        # Weekday < 5 (Mon-Fri)
        is_weekday = times_ist.dayofweek < 5

        # Time checks (minutes from midnight)
        open_minutes = MARKET_OPEN.hour * 60 + MARKET_OPEN.minute
        close_minutes = MARKET_CLOSE.hour * 60 + MARKET_CLOSE.minute

        minutes = times_ist.hour * 60 + times_ist.minute

        is_within_hours = (minutes >= open_minutes) & (minutes < close_minutes)

        # Holiday check
        # self.guard.trading_holidays is a Set[str]
        # Optimization: convert holidays to date objects
        holidays = {datetime.strptime(d, "%Y-%m-%d").date() for d in self.guard.trading_holidays}

        # np.isin with object array of dates
        is_not_holiday = ~np.isin(times_ist.date, list(holidays))

        open_mask = is_weekday & is_within_hours & is_not_holiday

        # 2. Session Closing Mask
        # We assume 5 minute buffer before HARD_CLOSE
        hard_close_minutes = HARD_CLOSE.hour * 60 + HARD_CLOSE.minute
        buffer_minutes = 5
        start_closing_minutes = hard_close_minutes - buffer_minutes

        # Logic: Current time >= start_closing_minutes
        closing_mask = minutes >= start_closing_minutes

        return open_mask, closing_mask
