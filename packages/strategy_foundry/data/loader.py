"""Data loader with Yahoo Finance fallback and caching"""
import os
import time
from datetime import datetime, timedelta
import pandas as pd
import requests
import structlog
from pathlib import Path
from typing import Optional, Dict

logger = structlog.get_logger(__name__)

CACHE_DIR = Path("packages/strategy_foundry/data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

class DataLoader:
    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }

    def get_data(self, symbol: str, timeframe: str, days: int = 60) -> pd.DataFrame:
        """
        Fetch OHLCV data.
        Tries cache first, then Yahoo Finance.

        Args:
            symbol: Yahoo ticker (e.g., ^NSEI)
            timeframe: 5m, 15m, 1d
            days: History length
        """
        cache_key = f"{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d')}"
        cache_path = CACHE_DIR / f"{cache_key}.csv"

        # 1. Try Cache
        if self.use_cache and cache_path.exists():
            try:
                df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                logger.info("Loaded from cache", symbol=symbol, timeframe=timeframe)
                return df
            except Exception as e:
                logger.warning("Cache read failed", error=str(e))

        # 2. Fetch from Yahoo
        df = self._fetch_yahoo(symbol, timeframe, days)

        # 3. Save Cache
        if not df.empty and self.use_cache:
            df.to_csv(cache_path)

        return df

    def _fetch_yahoo(self, symbol: str, timeframe: str, days: int) -> pd.DataFrame:
        """Lightweight Yahoo Finance fetcher using requests"""
        interval_map = {
            "5m": "5m",
            "15m": "15m",
            "1D": "1d",
            "1d": "1d"
        }

        yahoo_interval = interval_map.get(timeframe, "1d")

        # Yahoo limits intraday to 60 days
        if timeframe in ["5m", "15m"] and days > 59:
            days = 59

        start_dt = datetime.now() - timedelta(days=days)
        start_ts = int(start_dt.timestamp())
        end_ts = int(datetime.now().timestamp())

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            "symbol": symbol,
            "period1": start_ts,
            "period2": end_ts,
            "interval": yahoo_interval,
            "includePrePost": "false"
        }

        try:
            # Need a session to handle cookies sometimes, but simple GET often works for v8 chart
            # If 401/403, might need crumb ceremony. For now, try simple.
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
                logger.error("No data found in Yahoo response", symbol=symbol)
                return pd.DataFrame()

            result = data["chart"]["result"][0]
            if "timestamp" not in result or "indicators" not in result:
                return pd.DataFrame()

            timestamps = result["timestamp"]
            quote = result["indicators"]["quote"][0]

            df = pd.DataFrame({
                "open": quote["open"],
                "high": quote["high"],
                "low": quote["low"],
                "close": quote["close"],
                "volume": quote["volume"]
            }, index=pd.to_datetime(timestamps, unit="s", utc=True))

            # Convert to IST
            df.index = df.index.tz_convert("Asia/Kolkata")

            # Drop NaNs
            df.dropna(inplace=True)

            # Standardize columns
            df.index.name = "date"

            return df

        except Exception as e:
            logger.error("Yahoo fetch failed", symbol=symbol, error=str(e))
            # Fallback for testing/offline: random walk or error?
            # Return empty for now to fail gracefully
            return pd.DataFrame()

