"""
Data loader for Strategy Foundry.
Fetches daily OHLCV for NIFTY/SENSEX from Yahoo Finance (or cache).
"""
import csv
import io
import os
import time
from datetime import datetime, timedelta
import requests
import pandas as pd
import structlog
import yaml

# Local cache directory
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../configs/instrument_map.yaml")

logger = structlog.get_logger(__name__)

# Default map if config missing
DEFAULT_INSTRUMENTS = {
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN"
}

class DataLoader:
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        self.symbol_map = self._load_config()

    def _load_config(self) -> dict:
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    return yaml.safe_load(f)
            except Exception:
                pass
        return DEFAULT_INSTRUMENTS

    def get_data(self, symbol: str, days: int = 3650, force_refresh: bool = False) -> pd.DataFrame:
        """
        Get Daily OHLCV data for a symbol.
        1. Check cache.
        2. If missing/stale/force_refresh, download from Yahoo.
        3. Return normalized DataFrame.
        """
        ticker = self.symbol_map.get(symbol, symbol)
        cache_path = os.path.join(self.cache_dir, f"{symbol}.csv")

        # Check cache validity
        if not force_refresh and os.path.exists(cache_path):
            modified_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
            # If cache is younger than 12 hours, use it
            if datetime.now() - modified_time < timedelta(hours=12):
                logger.info(f"Loading {symbol} from cache")
                df = pd.read_csv(cache_path, parse_dates=["Date"], index_col="Date")
                return self._sanitize(df)

        # Download
        logger.info(f"Downloading {symbol} ({ticker})")
        df = self._download_yahoo(ticker, days)

        if df is not None and not df.empty:
            # Save to cache
            df.to_csv(cache_path)
            return self._sanitize(df)

        # Fallback to cache if download failed
        if os.path.exists(cache_path):
            logger.warning(f"Download failed for {symbol}, using stale cache")
            df = pd.read_csv(cache_path, parse_dates=["Date"], index_col="Date")
            return self._sanitize(df)

        raise ValueError(f"No data available for {symbol}")

    def _download_yahoo(self, ticker: str, days: int) -> pd.DataFrame:
        """
        Download data from Yahoo Finance JSON/CSV endpoint using requests.
        """
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)

        p1 = int(start_dt.timestamp())
        p2 = int(end_dt.timestamp())

        url = f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}?period1={p1}&period2={p2}&interval=1d&events=history&includeAdjustedClose=true"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }

        try:
            # Simple retry logic
            for _ in range(3):
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200:
                    return pd.read_csv(io.StringIO(r.text), parse_dates=["Date"], index_col="Date")
                elif r.status_code == 429:
                    # Rate limit
                    time.sleep(2)
                else:
                    logger.warning(f"Yahoo download error: {r.status_code} {r.text}")
                    break
        except Exception as e:
            logger.error(f"Download exception: {e}")

        return None

    def _sanitize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and normalize data.
        """
        # Ensure standard columns
        df.columns = [c.lower() for c in df.columns]
        required = ["open", "high", "low", "close", "volume"]

        # Yahoo sometimes gives 'adj close'. We prefer 'close' or 'adj close' if close missing?
        # Standard Yahoo CSV: Date, Open, High, Low, Close, Adj Close, Volume

        if "adj close" in df.columns:
            # Use Adj Close for backtesting to handle splits/dividends?
            # For indices like NIFTY, Close is usually fine.
            # Let's stick to Close for now as 'Adj Close' is often same for Indices (mostly).
            pass

        # Filter for valid rows
        df = df[required].dropna()

        # Convert index to Asia/Kolkata
        # Yahoo dates are usually naive YYYY-MM-DD. We assume they are session dates.
        # We will set them to 15:30 IST for consistency
        df.index = pd.to_datetime(df.index).tz_localize("Asia/Kolkata") + timedelta(hours=15, minutes=30)

        # Sort
        df = df.sort_index()

        # Remove duplicates
        df = df[~df.index.duplicated(keep='first')]

        return df
