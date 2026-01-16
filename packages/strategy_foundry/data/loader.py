"""Data Loader for Strategy Foundry"""
import os
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
from io import StringIO
import structlog
import yaml

logger = structlog.get_logger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CONFIG_DIR = Path(__file__).parent.parent / "configs"
INSTRUMENT_MAP_PATH = CONFIG_DIR / "instrument_map.yaml"

# Default config if file missing
DEFAULT_INSTRUMENT_MAP = {
    "NIFTY": {"research": "^NSEI", "proxy": "NIFTYBEES.NS"},
    "SENSEX": {"research": "^BSESN", "proxy": "SENSEXBEES.NS"} # Fallback examples
}

class DataLoader:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.instrument_map = self._load_map()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }

    def _load_map(self):
        if INSTRUMENT_MAP_PATH.exists():
             with open(INSTRUMENT_MAP_PATH) as f:
                return yaml.safe_load(f)
        return DEFAULT_INSTRUMENT_MAP

    def get_data(self, symbol: str, lookback_days: int = 2000) -> pd.DataFrame:
        """
        Get daily OHLCV data for a symbol.
        1. Check cache
        2. If stale/missing, download
        """
        mapping = self.instrument_map.get(symbol)
        if not mapping:
             raise ValueError(f"Unknown symbol: {symbol}")

        research_symbol = mapping["research"]
        file_path = self.cache_dir / f"{symbol}.csv"

        if self._is_cache_valid(file_path):
            df = pd.read_csv(file_path, parse_dates=["Date"], index_col="Date")
            logger.info("Loaded from cache", symbol=symbol, rows=len(df))
            return df

        # Download
        logger.info("Downloading data", symbol=symbol, ticker=research_symbol)
        df = self._download_yahoo(research_symbol, lookback_days)

        if df.empty and "proxy" in mapping:
            logger.warning("Primary download failed, trying proxy", symbol=symbol, proxy=mapping["proxy"])
            df = self._download_yahoo(mapping["proxy"], lookback_days)

        if not df.empty:
            df.to_csv(file_path)
            # Try parquet if available (optional)
            try:
                import pyarrow
                df.to_parquet(file_path.with_suffix(".parquet"))
            except ImportError:
                pass

        return df

    def _is_cache_valid(self, path: Path) -> bool:
        if not path.exists():
            return False

        # Check if modified today (simple check)
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return mtime.date() == datetime.now().date()

    def _download_yahoo(self, ticker: str, days: int) -> pd.DataFrame:
        """Download from Yahoo Finance query1 endpoint"""
        end = int(time.time())
        start = int((datetime.now() - timedelta(days=days)).timestamp())

        url = f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}?period1={start}&period2={end}&interval=1d&events=history"

        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                logger.error("Download failed", code=resp.status_code, text=resp.text[:100])
                return pd.DataFrame()

            df = pd.read_csv(StringIO(resp.text))

            # Normalize
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)
            df.sort_index(inplace=True)

            # Rename cols to lowercase
            df.rename(columns={
                "Open": "open", "High": "high", "Low": "low",
                "Close": "close", "Volume": "volume", "Adj Close": "adj_close"
            }, inplace=True)

            # Drop NaNs
            df.dropna(inplace=True)

            # Ensure unique index
            df = df[~df.index.duplicated(keep='first')]

            return df[["open", "high", "low", "close", "volume"]]

        except Exception as e:
            logger.error("Download exception", error=str(e))
            return pd.DataFrame()
