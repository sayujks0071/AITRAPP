"""
Data Loader
Manages loading, caching, and preprocessing of market data.
"""
import os
import pandas as pd
from datetime import datetime
import structlog
from pathlib import Path
from packages.strategy_foundry.data.sources import DataSources
from packages.strategy_foundry.adapters.core_market_hours import IST
from packages.strategy_foundry.adapters.core_data_provider import CoreDataProvider

logger = structlog.get_logger(__name__)

CACHE_DIR = Path("packages/strategy_foundry/data/cache")

class DataLoader:
    def __init__(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def get_data(self, symbol: str, timeframe: str, force_refresh: bool = False) -> pd.DataFrame:
        """
        Get OHLCV data for symbol and timeframe.
        Tries CoreProvider -> Cache -> Yahoo -> Fallback
        """
        # 1. Try Core Provider (if implemented)
        core_data = CoreDataProvider.get_ohlcv(symbol, timeframe)
        if core_data is not None and not core_data.empty:
            return self._process_data(core_data, timeframe)

        # 2. Check Cache
        cache_file = CACHE_DIR / f"{symbol}_{timeframe}.csv"
        if not force_refresh and cache_file.exists():
            # Check age - refresh if older than 1 hour for intraday, 12 hours for daily
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            age = datetime.now() - mtime
            max_age = 3600 if timeframe in ["5m", "15m"] else 43200

            if age.total_seconds() < max_age:
                try:
                    df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                    return self._process_data(df, timeframe)
                except Exception as e:
                    logger.warning(f"Corrupt cache for {symbol}: {e}")

        # 3. Download from Yahoo
        logger.info(f"Fetching fresh data for {symbol} {timeframe}")
        df = DataSources.get_yahoo_data(symbol, timeframe)

        if not df.empty:
            # Save to cache
            df.to_csv(cache_file)
            return self._process_data(df, timeframe)

        logger.error(f"Failed to load data for {symbol} {timeframe}")
        return pd.DataFrame()

    def _process_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Standardize data format and timezone"""
        if df.empty:
            return df

        # Ensure UTC then convert to IST
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')

        df.index = df.index.tz_convert(IST)

        # Filter for market hours (09:15 - 15:30)
        # Assuming index is DatetimeIndex

        if timeframe in ["5m", "15m"]:
            # Simple filter: keeping only 09:15 to 15:30 range
            # 09:15 is the start. 15:25 is close.
            # We'll be permissive and keep 09:15 to 15:30
            # Time components
            mask = (
                (df.index.time >= datetime.strptime("09:15", "%H:%M").time()) &
                (df.index.time <= datetime.strptime("15:30", "%H:%M").time())
            )
            df = df[mask]

        return df.sort_index()
