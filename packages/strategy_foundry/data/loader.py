import os
import csv
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import requests
import pandas as pd
import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Yahoo Finance mapping
SYMBOLS = {
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN"
}

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"

class DataLoader:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir

    def get_history(self, instrument: str, lookback_days: int = 365*5) -> pd.DataFrame:
        """
        Get historical daily data for instrument.
        Returns DataFrame with index 'date' (datetime, Asia/Kolkata) and cols: open, high, low, close, volume.
        """
        symbol = SYMBOLS.get(instrument, instrument)
        cache_file = self.cache_dir / f"{instrument}.csv"

        # Check cache validity (updated today)
        if self._is_cache_fresh(cache_file):
            logger.info(f"Loading {instrument} from cache")
            df = pd.read_csv(cache_file, parse_dates=["date"], index_col="date")
            # Ensure index is tz-aware if not already
            if df.index.tz is None:
                df.index = df.index.tz_localize("Asia/Kolkata")
            else:
                 df.index = df.index.tz_convert("Asia/Kolkata")
            return df

        # Download
        logger.info(f"Downloading {instrument} ({symbol}) from Yahoo Finance")
        try:
            df = self._download_yahoo(symbol, lookback_days)
            if not df.empty:
                # Save to cache
                df.to_csv(cache_file)
            return df
        except Exception as e:
            logger.error(f"Failed to download {instrument}: {e}")
            # Fallback to cache even if stale
            if cache_file.exists():
                logger.warning(f"Falling back to stale cache for {instrument}")
                df = pd.read_csv(cache_file, parse_dates=["date"], index_col="date")
                if df.index.tz is None:
                    df.index = df.index.tz_localize("Asia/Kolkata")
                else:
                    df.index = df.index.tz_convert("Asia/Kolkata")
                return df
            raise

    def _is_cache_fresh(self, filepath: Path) -> bool:
        if not filepath.exists():
            return False

        mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
        now = datetime.now()

        # Fresh if modified today (and market likely closed or data updated)
        # Simple rule: if file is from today, it's fresh enough for hourly runs
        # (assuming we update it on first run of day)
        # Actually, if we run hourly, we might want to update if cache is > 1 hour old?
        # Yahoo daily data updates once a day. Let's say if it's from today (local time), it's good.

        return mtime.date() == now.date()

    def _download_yahoo(self, symbol: str, lookback_days: int) -> pd.DataFrame:
        end_ts = int(time.time())
        start_ts = int((datetime.now() - timedelta(days=lookback_days)).timestamp())

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            "period1": start_ts,
            "period2": end_ts,
            "interval": "1d",
            "events": "history"
        }
        headers = {"User-Agent": USER_AGENT}

        resp = requests.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        if "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
            logger.warning("No data found in Yahoo response")
            return pd.DataFrame()

        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        indicators = result["indicators"]["quote"][0]

        df = pd.DataFrame({
            "date": pd.to_datetime(timestamps, unit="s", utc=True).tz_convert("Asia/Kolkata"),
            "open": indicators["open"],
            "high": indicators["high"],
            "low": indicators["low"],
            "close": indicators["close"],
            "volume": indicators["volume"]
        })

        # Drop rows with NaNs (sometimes Yahoo returns nulls)
        df.dropna(inplace=True)

        # Sort and index
        df.set_index("date", inplace=True)
        df.sort_index(inplace=True)

        # Sanity check: remove rows with 0 or negative prices
        df = df[(df["open"] > 0) & (df["high"] > 0) & (df["low"] > 0) & (df["close"] > 0)]

        # Ensure high >= low
        df = df[df["high"] >= df["low"]]

        return df

    def update_cache(self, lookback_days: int = 365*5):
        """Update cache for all symbols"""
        for name in SYMBOLS:
            try:
                self.get_history(name, lookback_days)
            except Exception as e:
                logger.error(f"Failed to update cache for {name}: {e}")
