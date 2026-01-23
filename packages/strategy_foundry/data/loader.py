import os
import time
import requests
import pandas as pd
import structlog
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = structlog.get_logger(__name__)

class DataLoader:
    def __init__(self, cache_dir: str = "packages/strategy_foundry/data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://query1.finance.yahoo.com/v7/finance/download"
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"

    def get_data(self, symbol: str, timeframe: str, days: int = 60, use_cache: bool = True) -> pd.DataFrame:
        """
        Get OHLCV data for a symbol.

        Args:
            symbol: Yahoo Finance symbol (e.g. ^NSEI)
            timeframe: "5m", "15m", "1d"
            days: Number of days of history to fetch
            use_cache: Whether to use cached data if available and recent

        Returns:
            DataFrame with Open, High, Low, Close, Volume index by datetime (Asia/Kolkata)
        """
        cache_file = self.cache_dir / f"{symbol}_{timeframe}.csv"

        # Check cache validity (simple check: modified today)
        if use_cache and cache_file.exists():
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - mtime < timedelta(minutes=60): # Refresh hourly
                logger.info("Loading from cache", symbol=symbol, timeframe=timeframe)
                return self._load_csv(cache_file)

        # Download
        logger.info("Downloading data", symbol=symbol, timeframe=timeframe)
        df = self._download(symbol, timeframe, days)

        if df is not None and not df.empty:
            df.to_csv(cache_file)
            return df

        # Fallback to cache if download failed
        if cache_file.exists():
             logger.warning("Download failed, falling back to stale cache", symbol=symbol)
             return self._load_csv(cache_file)

        return pd.DataFrame()

    def _download(self, symbol: str, timeframe: str, days: int) -> Optional[pd.DataFrame]:
        end_ts = int(time.time())
        start_ts = int((datetime.now() - timedelta(days=days)).timestamp())

        # Map timeframe
        interval_map = {
            "5m": "5m",
            "15m": "15m",
            "1D": "1d", # Yahoo uses 1d
            "1d": "1d"
        }
        interval = interval_map.get(timeframe, "1d")

        url = f"{self.base_url}/{symbol}"
        params = {
            "period1": start_ts,
            "period2": end_ts,
            "interval": interval,
            "events": "history"
        }
        headers = {"User-Agent": self.user_agent}

        try:
            response = requests.get(url, params=params, headers=headers)
            if response.status_code == 429:
                logger.warning("Rate limit hit", symbol=symbol)
                time.sleep(2)
                return None

            if response.status_code != 200:
                logger.error("Download error", status=response.status_code, text=response.text[:100])
                return None

            # Save to temp file to read with pandas
            temp_path = self.cache_dir / f"temp_{symbol}_{timeframe}.csv"
            with open(temp_path, "wb") as f:
                f.write(response.content)

            df = self._load_csv(temp_path)
            temp_path.unlink(missing_ok=True)
            return df

        except Exception as e:
            logger.error("Download exception", error=str(e))
            return None

    def _load_csv(self, path: Path) -> pd.DataFrame:
        try:
            df = pd.read_csv(path)

            # Standardize columns
            df.columns = [c.lower() for c in df.columns]
            rename_map = {
                "date": "datetime",
                "datetime": "datetime"
            }
            df = df.rename(columns=rename_map)

            # Parse datetime
            # Yahoo 5m/15m has 'Datetime' column (UTC usually), 1d has 'Date'
            if "datetime" in df.columns:
                 # Attempt to parse.
                 # Intraday from Yahoo is often UTC. We want Asia/Kolkata.
                 df["datetime"] = pd.to_datetime(df["datetime"], utc=True).dt.tz_convert("Asia/Kolkata")

            df = df.set_index("datetime").sort_index()

            # Ensure numeric
            cols = ["open", "high", "low", "close", "volume"]
            for c in cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce")

            df = df.dropna()
            return df

        except Exception as e:
            logger.error("CSV parse error", path=path, error=str(e))
            return pd.DataFrame()
