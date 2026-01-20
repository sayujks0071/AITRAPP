"""Data loader with caching and timezone handling"""
import os
import pandas as pd
import pytz
import structlog
from datetime import datetime, timedelta
from typing import Optional, Dict

from packages.strategy_foundry.data.sources import YahooSource

logger = structlog.get_logger(__name__)

class DataLoader:
    def __init__(self, cache_dir: str = "packages/strategy_foundry/data/cache"):
        self.cache_dir = cache_dir
        self.source = YahooSource()
        self.ist = pytz.timezone("Asia/Kolkata")

        os.makedirs(self.cache_dir, exist_ok=True)

    def get_data(self, symbol: str, timeframe: str, force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """
        Get OHLCV data for symbol and timeframe.
        Attempts to load from cache first.
        If cache is missing or stale/incomplete (logic can be improved), fetches from source.

        Args:
            symbol: Symbol (e.g. ^NSEI)
            timeframe: Timeframe (e.g. 1d, 5m, 15m)
            force_refresh: If True, ignore cache and fetch fresh.

        Returns:
            DataFrame in IST with index as datetime.
        """
        cache_path = os.path.join(self.cache_dir, f"{symbol}_{timeframe}.csv")

        # Check cache
        if not force_refresh and os.path.exists(cache_path):
            try:
                # Check modification time, if it's very old for intraday, maybe refresh?
                # For now rely on explicit refresh or just load it.
                # In hourly run, we might want to refresh if it's market hours.

                df = pd.read_csv(cache_path, index_col="timestamp", parse_dates=True)

                # Check staleness - for intraday, if last bar is yesterday and today is trading day, we might need update.
                # For now, simple logic: if file exists and we didn't force refresh, return it.
                # But typically caller (hourly runner) will decide when to force refresh.
                logger.info("Loaded from cache", symbol=symbol, timeframe=timeframe, rows=len(df))

                # Ensure index is timezone aware (read_csv might lose it or make it UTC)
                if df.index.tz is None:
                    # Assuming cache was saved as UTC isoformat
                    df.index = df.index.tz_localize("UTC")

                return self._process_dataframe(df)
            except Exception as e:
                logger.warning("Failed to read cache", path=cache_path, error=str(e))

        # Fetch from source
        # Mapping timeframe/range
        if timeframe == "1d":
            fetch_range = "max" # or 10y
        elif timeframe in ["5m", "15m"]:
            fetch_range = "60d" # Yahoo limitation for intraday
        else:
            fetch_range = "1mo" # default

        df = self.source.fetch_ohlcv(symbol, timeframe, range_=fetch_range)

        if df is not None and not df.empty:
            # Save to cache (raw UTC)
            df.to_csv(cache_path)
            logger.info("Fetched and cached", symbol=symbol, timeframe=timeframe, rows=len(df))
            return self._process_dataframe(df)

        return None

    def _process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Post-process dataframe:
        1. Convert to IST
        2. Filter market hours (09:15 - 15:30)
        3. Sort index
        """
        if df.empty:
            return df

        # Convert to IST
        if df.index.tz is None:
             df.index = df.index.tz_localize("UTC")

        df.index = df.index.tz_convert(self.ist)

        # Filter Market Hours (09:15 to 15:30)
        # We allow a bit of buffer if needed, but strict is better for backtest

        # Construct boolean mask
        # time() returns time object
        mask = (df.index.time >= datetime.strptime("09:15", "%H:%M").time()) & \
               (df.index.time <= datetime.strptime("15:30", "%H:%M").time())

        df = df[mask]

        # Sort
        df.sort_index(inplace=True)

        return df

    def update_cache(self, symbol: str, timeframe: str):
        """Force update cache"""
        self.get_data(symbol, timeframe, force_refresh=True)
