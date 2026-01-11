import os
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
import structlog
import yaml

logger = structlog.get_logger(__name__)

class DataLoader:
    def __init__(self, cache_dir: str = "packages/strategy_foundry/data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"

    def get_data(self, symbol: str, timeframe: str, days: int = 60, force_refresh: bool = False) -> pd.DataFrame:
        """
        Get OHLCV data for a symbol.
        1. Check cache
        2. If missing or stale or force_refresh, fetch from Yahoo
        3. Save to cache
        4. Return DataFrame
        """
        # Map timeframe to Yahoo interval
        tf_map = {
            "5m": "5m",
            "15m": "15m",
            "1h": "60m",
            "1d": "1d"
        }
        interval = tf_map.get(timeframe)
        if not interval:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        # Sanitize symbol for filename
        safe_symbol = symbol.replace("^", "")
        cache_file = self.cache_dir / f"{safe_symbol}_{timeframe}.csv"

        df = None
        if not force_refresh and cache_file.exists():
            # Check age (simple check: if file is older than 1 hour for intraday, refresh)
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            age = datetime.now() - mtime
            is_stale = False

            # Intraday data needs to be fresh if market is open or recently closed
            if timeframe in ["5m", "15m"]:
                if age.total_seconds() > 3600: # 1 hour
                    is_stale = True
            else:
                 if age.days > 1:
                     is_stale = True

            if not is_stale:
                try:
                    df = pd.read_csv(cache_file)
                    df["date"] = pd.to_datetime(df["date"], utc=True)
                    df = df.set_index("date").sort_index()
                    # Convert to Asia/Kolkata
                    df.index = df.index.tz_convert("Asia/Kolkata")
                    logger.info("Loaded from cache", symbol=symbol, timeframe=timeframe, rows=len(df))
                    return df
                except Exception as e:
                    logger.warning("Cache load failed", error=str(e))

        # Fetch from Yahoo
        logger.info("Fetching from Yahoo", symbol=symbol, interval=interval)
        try:
            df = self._fetch_yahoo(symbol, interval, days)
            if df is not None and not df.empty:
                # Save to cache
                df.to_csv(cache_file)
                # Reload to ensure consistency with cache loading path
                df = pd.read_csv(cache_file)
                df["date"] = pd.to_datetime(df["date"], utc=True)
                df = df.set_index("date").sort_index()
                df.index = df.index.tz_convert("Asia/Kolkata")
                return df
        except Exception as e:
            logger.error("Fetch failed", symbol=symbol, error=str(e))
            if cache_file.exists():
                logger.info("Falling back to stale cache")
                df = pd.read_csv(cache_file)
                df["date"] = pd.to_datetime(df["date"], utc=True)
                df = df.set_index("date").sort_index()
                df.index = df.index.tz_convert("Asia/Kolkata")
                return df

        return pd.DataFrame()

    def _fetch_yahoo(self, symbol: str, interval: str, days: int) -> Optional[pd.DataFrame]:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)

        p1 = int(start_dt.timestamp())
        p2 = int(end_dt.timestamp())

        url = f"https://query1.finance.yahoo.com/v7/finance/download/{symbol}?period1={p1}&period2={p2}&interval={interval}&events=history&includeAdjustedClose=true"

        headers = {"User-Agent": self.user_agent}

        # Yahoo requires a cookie and crumb (sometimes).
        # For simplicity, we try without first. If it fails, we might need a more complex fetcher.
        # But for many public symbols it works with just User-Agent.
        # If this fails frequently, we can try `yfinance` logic implementation but using requests.
        # However, requirements forbid heavy deps.
        # We will try a session with a simple get to home page to set cookies if needed.

        session = requests.Session()
        session.headers.update(headers)

        # Warm up session
        try:
            session.get("https://finance.yahoo.com", timeout=5)
        except:
            pass

        response = session.get(url, timeout=10)
        response.raise_for_status()

        lines = response.text.strip().split("\n")
        if len(lines) < 2:
            return None

        from io import StringIO
        csv_data = StringIO(response.text)
        df = pd.read_csv(csv_data)

        # Rename cols to lower case
        df.columns = [c.lower() for c in df.columns]
        # Yahoo cols: date, open, high, low, close, adj close, volume

        if "date" not in df.columns:
            # Sometimes Yahoo returns error in text
            return None

        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.set_index("date").sort_index()

        # Drop adj close
        if "adj close" in df.columns:
            df = df.drop(columns=["adj close"])

        return df

    def filter_market_hours(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter rows to keep only market hours (09:15 - 15:30 IST).
        """
        if df.empty:
            return df

        # Ensure index is Asia/Kolkata
        if df.index.tz is None:
             df.index = df.index.tz_localize("Asia/Kolkata")
        elif str(df.index.tz) != "Asia/Kolkata":
             df.index = df.index.tz_convert("Asia/Kolkata")

        # Filter 09:15 to 15:30
        mask = (
            (df.index.time >= datetime.strptime("09:15", "%H:%M").time()) &
            (df.index.time <= datetime.strptime("15:30", "%H:%M").time())
        )
        return df[mask]
