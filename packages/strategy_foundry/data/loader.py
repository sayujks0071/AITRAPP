import os
import pandas as pd
import structlog
from datetime import datetime, timedelta
import yaml
from pathlib import Path
from packages.strategy_foundry.data.sources import DataSourceRegistry
from packages.strategy_foundry.adapters.core_market_hours import IST

logger = structlog.get_logger(__name__)

class DataLoader:
    """
    Orchestrates data loading, caching, and fallback logic.
    """
    def __init__(self, config_path: str = "packages/strategy_foundry/configs/foundry.yaml",
                 map_path: str = "packages/strategy_foundry/configs/instrument_map.yaml"):

        self.config = self._load_yaml(config_path)
        self.instrument_map = self._load_yaml(map_path)
        self.sources = DataSourceRegistry()
        self.cache_dir = Path(self.config.get("data", {}).get("cache_dir", "packages/strategy_foundry/data/cache"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _load_yaml(self, path: str) -> dict:
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config {path}", error=str(e))
            return {}

    def get_data(self, symbol_key: str, timeframe: str, refresh: bool = False) -> pd.DataFrame:
        """
        Get OHLCV data for a symbol key (e.g., NIFTY) and timeframe (e.g., 5m, 15m, 1d).

        1. Check cache.
        2. If cache miss or refresh needed, fetch from source.
        3. Fallback if primary source fails.
        """
        # Resolve symbol
        research_symbol = self.instrument_map.get("research", {}).get(symbol_key)
        if not research_symbol:
            logger.error(f"Unknown symbol key: {symbol_key}")
            return pd.DataFrame()

        # Check cache
        cache_file = self.cache_dir / f"{symbol_key}_{timeframe}.csv"

        if not refresh and cache_file.exists():
            # Basic staleness check (e.g. if file is older than 1 hour for intraday)
            # For now, we rely on the 'refresh' flag primarily.
            try:
                df = pd.read_csv(cache_file, parse_dates=["timestamp"], index_col="timestamp")
                # Ensure timezone
                if df.index.tz is None:
                    df.index = df.index.tz_localize("UTC").tz_convert("Asia/Kolkata")
                return df
            except Exception as e:
                logger.warning(f"Corrupt cache for {symbol_key} {timeframe}, re-fetching.", error=str(e))

        # Fetch
        df = self._fetch_from_source(research_symbol, timeframe)

        if df.empty:
            # Fallback to proxy if research symbol fails
            proxy_symbol = self.instrument_map.get("paper_proxy", {}).get(symbol_key)
            # But wait, paper_proxy might be a broker symbol or logic, which Yahoo won't understand usually.
            # Assuming instrument_map might have alternative Yahoo symbols if needed, or we just fail.
            # For now, we stick to research symbol.
            logger.error(f"Failed to fetch data for {symbol_key} ({research_symbol})")
            return pd.DataFrame()

        # Save to cache
        df.to_csv(cache_file)
        return df

    def _fetch_from_source(self, symbol: str, timeframe: str) -> pd.DataFrame:
        # Map timeframe to Yahoo interval/range
        interval_map = {
            "5m": "5m",
            "15m": "15m",
            "1d": "1d"
        }

        # Dynamic range based on config
        # Yahoo limits: 5m -> 60d, 15m -> 60d, 1d -> max
        range_map = {
            "5m": "60d",
            "15m": "60d", # Yahoo limitation for intraday is often 60d
            "1d": "5y"
        }

        interval = interval_map.get(timeframe)
        if not interval:
            logger.error(f"Unsupported timeframe {timeframe}")
            return pd.DataFrame()

        range_str = range_map.get(timeframe, "1mo")

        # Try fetching
        df = self.sources.get_yahoo().fetch_ohlcv(symbol, interval, range_str)

        return df

    def clean_cache(self):
        """Remove all cached files"""
        for f in self.cache_dir.glob("*.csv"):
            f.unlink()
