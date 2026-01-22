from datetime import datetime, time
import pytz
import numpy as np
import pandas as pd
from typing import Optional, Tuple
from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE, HARD_CLOSE

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

    def get_masks(self, times: pd.DatetimeIndex, buffer_minutes: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns boolean masks for (is_market_open, is_session_closing).
        Vectorized implementation for performance.
        """
        # Ensure IST
        if times.tz is None:
            times_ist = times.tz_localize("Asia/Kolkata")
        else:
            times_ist = times.tz_convert("Asia/Kolkata")

        # 1. Market Open Mask
        # Conditions:
        # - Not Weekend (Sat=5, Sun=6)
        # - Not Holiday
        # - Time within 09:15 - 15:20

        # Weekday
        weekday = times_ist.dayofweek
        is_weekday = weekday < 5

        # Holidays
        if self.guard.trading_holidays:
            # Normalize to midnight for date comparison
            times_midnight = times_ist.normalize()

            # Convert holidays to tz-aware timestamps at midnight (IST)
            # self.guard.trading_holidays is set of strings "YYYY-MM-DD"
            holidays_list = list(self.guard.trading_holidays)
            if holidays_list:
                holidays_idx = pd.DatetimeIndex(holidays_list).tz_localize("Asia/Kolkata")
                is_not_holiday = ~times_midnight.isin(holidays_idx)
            else:
                 is_not_holiday = np.ones(len(times), dtype=bool)
        else:
            is_not_holiday = np.ones(len(times), dtype=bool)

        # Time
        # Convert to minutes from midnight
        minutes = times_ist.hour * 60 + times_ist.minute

        market_open_mins = MARKET_OPEN.hour * 60 + MARKET_OPEN.minute
        market_close_mins = MARKET_CLOSE.hour * 60 + MARKET_CLOSE.minute

        is_time_open = (minutes >= market_open_mins) & (minutes < market_close_mins)

        # Combined Open Mask
        is_market_open_mask = is_weekday & is_not_holiday & is_time_open

        # 2. Session Closing Mask
        # Conditions:
        # - Time >= 15:20 (HARD_CLOSE - buffer)

        hard_close_mins = HARD_CLOSE.hour * 60 + HARD_CLOSE.minute
        closing_threshold = hard_close_mins - buffer_minutes

        is_session_closing_mask = (minutes >= closing_threshold)

        # Ensure return type is numpy array
        if hasattr(is_market_open_mask, "to_numpy"):
             is_market_open_mask = is_market_open_mask.to_numpy()
        if hasattr(is_session_closing_mask, "to_numpy"):
             is_session_closing_mask = is_session_closing_mask.to_numpy()

        return is_market_open_mask, is_session_closing_mask
