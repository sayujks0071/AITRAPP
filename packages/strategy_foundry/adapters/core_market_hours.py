"""
Market hours adapter using core logic but optimized for foundry.
"""
from datetime import datetime, time
import pytz
from packages.core.market_hours import MarketHoursGuard, MARKET_OPEN, MARKET_CLOSE, HARD_CLOSE, IST

class FoundryMarketHours:
    def __init__(self):
        self.guard = MarketHoursGuard()

    def is_market_open(self, dt: datetime = None) -> bool:
        return self.guard.is_market_open(dt)

    def get_session_close(self) -> time:
        return MARKET_CLOSE

    def get_hard_close(self) -> time:
        return HARD_CLOSE

    def is_intraday_window(self, dt: datetime) -> bool:
        """Check if dt is within valid intraday trading window (excluding opening/closing buffers if any)"""
        # Simple check for now: just market open status
        return self.guard.is_market_open(dt)

    def filter_market_hours(self, df: 'pd.DataFrame') -> 'pd.DataFrame':
        """Filter dataframe to only include market hours."""
        if df.empty:
            return df

        # Assume df index is datetime (tz-aware or naive assumed IST)
        # Helper to check time. fast vectorize?
        # For now, stick to pandas indexing

        indexer = df.index.indexer_at_time(MARKET_OPEN, HARD_CLOSE)
        # Wait, indexer_at_time is specific times.
        # between_time is better.

        # We need to handle 09:15 to 15:29 inclusive
        # Hard close is 15:25, so we should probably filter data after 15:30 anyway.

        return df.between_time("09:15", "15:29")
