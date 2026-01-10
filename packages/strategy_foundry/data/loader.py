"""
Data loader and caching layer.
"""
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import pandas as pd
import structlog
import yaml

from packages.strategy_foundry.data.sources import YahooSource

logger = structlog.get_logger(__name__)

class DataLoader:
    def __init__(self, config_path: str = "packages/strategy_foundry/configs/foundry.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.cache_dir = Path("packages/strategy_foundry/data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load instrument map
        with open("packages/strategy_foundry/configs/instrument_map.yaml", "r") as f:
            self.instrument_map = yaml.safe_load(f)

        self.source = YahooSource()

    def get_data(self, symbol: str, timeframe: str, force_refresh: bool = False) -> pd.DataFrame:
        """
        Get OHLCV data for a symbol and timeframe.
        Prioritizes cache, then fetches from source.

        Args:
            symbol: Common name (e.g. NIFTY) or Yahoo symbol
            timeframe: 5m, 15m, 1d

        Returns:
            DataFrame with DatetimeIndex and columns: Open, High, Low, Close, Volume
        """
        # Resolve symbol to Yahoo symbol
        yahoo_symbol = self.instrument_map.get("research", {}).get(symbol, symbol)

        # Determine cache file
        cache_file = self.cache_dir / f"{symbol}_{timeframe}.csv"

        df = None
        if not force_refresh and cache_file.exists():
            try:
                # Check cache age
                mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                # If cache is older than 1 hour and it's trading hours, maybe refresh?
                # For now, let's just rely on force_refresh flag usually set by the hourly runner

                # When saving we don't specify index_label so it defaults to "Date" if we index was named "Date"
                # But to_csv keeps index name.
                df = pd.read_csv(cache_file)
                if "Date" in df.columns:
                     df["Date"] = pd.to_datetime(df["Date"])
                     df.set_index("Date", inplace=True)
                elif "Unnamed: 0" in df.columns:
                     # sometimes happens if index name is missing
                     df.rename(columns={"Unnamed: 0": "Date"}, inplace=True)
                     df["Date"] = pd.to_datetime(df["Date"])
                     df.set_index("Date", inplace=True)

                logger.info("Loaded from cache", symbol=symbol, timeframe=timeframe)
            except Exception as e:
                logger.warning("Failed to read cache", error=str(e))

        if df is None or force_refresh:
            # Determine days to fetch
            days = self.config["defaults"].get("daily_data_days", 365)
            if timeframe in ["5m", "15m"]:
                days = self.config["defaults"].get("intraday_data_days", 59) # Yahoo limits intraday usually

            df = self.source.download_csv(yahoo_symbol, timeframe, days)

            if df is not None and not df.empty:
                # Save to cache
                df.to_csv(cache_file)
                logger.info("Fetched and cached", symbol=symbol, timeframe=timeframe)
            elif df is None and cache_file.exists():
                 # Fallback to cache if download fails
                 logger.warning("Download failed, falling back to stale cache", symbol=symbol)
                 df = pd.read_csv(cache_file, parse_dates=["Date"], index_col="Date")

        if df is None:
             raise ValueError(f"No data available for {symbol} {timeframe}")

        # Filter market hours if intraday
        if timeframe in ["5m", "15m"]:
            df = self._filter_market_hours(df)

        return df

    def _filter_market_hours(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter rows to keep only market hours (09:15 - 15:30 IST).
        """
        start = datetime.strptime(self.config["defaults"]["market_start"], "%H:%M").time()
        end = datetime.strptime(self.config["defaults"]["market_end"], "%H:%M").time()

        # This assumes naive timestamps in IST (which we set in sources.py)
        # Use boolean mask for filtering
        times = df.index.time
        mask = (times >= start) & (times <= end)
        return df[mask]
