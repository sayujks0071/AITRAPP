"""Data Loader for Strategy Foundry"""
import datetime
import os
import pandas as pd
import requests
import structlog
from pathlib import Path
from typing import Optional, Dict

logger = structlog.get_logger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"

# Ensure cache directory exists
CACHE_DIR.mkdir(parents=True, exist_ok=True)

YAHOO_URL = "https://query1.finance.yahoo.com/v7/finance/download/{symbol}"

# Mapping internal symbol to Yahoo Finance symbol
SYMBOL_MAP = {
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN",
    "BANKNIFTY": "^NSEBANK",
}

class DataLoader:
    """
    Loads daily historical data for indices.
    Priority: Cache -> Yahoo Finance Download
    """

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir

    def get_data(self, symbol: str, lookback_days: int = 2000, force_refresh: bool = False) -> pd.DataFrame:
        """
        Get daily OHLCV data for a symbol.

        Args:
            symbol: Internal symbol name (e.g., "NIFTY")
            lookback_days: Number of days of history to fetch
            force_refresh: If True, ignore cache and download fresh

        Returns:
            DataFrame with Index=Date (timezone aware Asia/Kolkata), columns=[open, high, low, close, volume]
        """
        yahoo_symbol = SYMBOL_MAP.get(symbol, symbol)
        cache_file = self.cache_dir / f"{symbol}.csv"

        # Check cache validity (simple check: modified today)
        if not force_refresh and cache_file.exists():
            mod_time = datetime.datetime.fromtimestamp(cache_file.stat().st_mtime)
            # If cache is from today (and market closed or whatever), it might be good.
            # For simplicity, if it's less than 12 hours old, use it.
            if (datetime.datetime.now() - mod_time).total_seconds() < 12 * 3600:
                try:
                    df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                    # Normalize index to Asia/Kolkata if not already
                    if df.index.tz is None:
                        df.index = df.index.tz_localize("UTC").tz_convert("Asia/Kolkata")
                    else:
                        df.index = df.index.tz_convert("Asia/Kolkata")

                    logger.info("Loaded data from cache", symbol=symbol, rows=len(df))
                    return df
                except Exception as e:
                    logger.warning("Failed to load cache, re-downloading", symbol=symbol, error=str(e))

        return self._download_and_cache(symbol, yahoo_symbol, lookback_days)

    def _download_and_cache(self, symbol: str, yahoo_symbol: str, lookback_days: int) -> pd.DataFrame:
        """Download from Yahoo Finance and save to CSV"""
        logger.info("Downloading data", symbol=symbol, yahoo_symbol=yahoo_symbol)

        end_dt = datetime.datetime.now()
        start_dt = end_dt - datetime.timedelta(days=lookback_days)

        # Yahoo expects unix timestamps
        period1 = int(start_dt.timestamp())
        period2 = int(end_dt.timestamp())

        params = {
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true"
        }

        url = YAHOO_URL.format(symbol=yahoo_symbol)
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            # Save raw content to temp file or parse directly
            # Response is CSV
            from io import StringIO
            csv_data = StringIO(response.text)

            df = pd.read_csv(csv_data)

            # Clean up
            df.columns = [c.lower() for c in df.columns]
            df = df.rename(columns={"date": "timestamp", "adj close": "adj_close"})

            # Standardize
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp")

            # Drop rows with NaN in OHLC
            df = df.dropna(subset=["open", "high", "low", "close"])

            # Timezone handling
            # Yahoo daily data is usually market local time (IST for NSE), but recorded as "date" (midnight).
            # We treat it as market close or just date.
            # Let's localize to Asia/Kolkata
            if df.index.tz is None:
                df.index = df.index.tz_localize("Asia/Kolkata")

            # Ensure columns
            required_cols = ["open", "high", "low", "close", "volume"]
            # If volume is 0/NaN, fill with 0
            if "volume" not in df.columns:
                df["volume"] = 0
            df["volume"] = df["volume"].fillna(0)

            df = df[required_cols]

            # Save to cache
            cache_file = self.cache_dir / f"{symbol}.csv"
            df.to_csv(cache_file)
            logger.info("Cached data", symbol=symbol, path=str(cache_file))

            return df

        except Exception as e:
            logger.error("Failed to download data", symbol=symbol, error=str(e))
            # Return empty DF on failure? Or raise?
            # Raise so we know something is wrong
            raise
