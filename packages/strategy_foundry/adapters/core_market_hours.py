"""Adapter for core market hours with vectorized support"""
import pandas as pd
import numpy as np
from datetime import time
from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE, HARD_CLOSE, IST

class MarketHoursAdapter(MarketHoursGuard):
    """
    Adapter extending core MarketHoursGuard with vectorized operations
    for efficient backtesting.
    """

    def get_masks(self, index: pd.DatetimeIndex):
        """
        Generate boolean masks for market hours.

        Args:
            index: DatetimeIndex in UTC or naive (assumed IST if naive, but safe to convert)

        Returns:
            (is_open, is_session_start, is_session_end)
        """
        # Ensure index is timezone aware (IST)
        if index.tz is None:
            # If naive, assume IST
            index = index.tz_localize(IST)
        else:
            index = index.tz_convert(IST)

        # 1. Holiday/Weekend mask
        # Vectorized weekday check (Sat=5, Sun=6)
        is_weekday = index.dayofweek < 5

        # Vectorized holiday check
        # We need to check if date string is in trading_holidays set
        # This is slower but done once per backtest
        # Optimization: Create a set of dates from index and intersect with holidays
        unique_dates = pd.to_datetime(index.date).unique()
        holiday_dates = pd.to_datetime(list(self.trading_holidays)).date
        holidays_in_range = set(holiday_dates).intersection(set(unique_dates.date))

        is_not_holiday = ~index.normalize().isin(holidays_in_range)

        is_trading_day = is_weekday & is_not_holiday

        # 2. Time of day mask
        # Convert times to minutes for easier comparison
        minutes = index.hour * 60 + index.minute

        open_minutes = MARKET_OPEN.hour * 60 + MARKET_OPEN.minute
        close_minutes = MARKET_CLOSE.hour * 60 + MARKET_CLOSE.minute # 15:20
        hard_close_minutes = HARD_CLOSE.hour * 60 + HARD_CLOSE.minute # 15:25

        # Is Open (Entry allowed)
        is_open_time = (minutes >= open_minutes) & (minutes < close_minutes)
        is_open = is_trading_day & is_open_time

        # Is Session Start (first bar of day)
        # Often simpler to just say it's the first bar >= 09:15
        is_session_start = is_trading_day & (minutes == open_minutes)

        # Is Session End (last bar before close or at hard close)
        # For 5m bars, 15:25 is the hard close.
        # We flag the bar AT or AFTER which we must be flat.
        is_session_end = is_trading_day & (minutes >= hard_close_minutes)

        return is_open, is_session_start, is_session_end
