"""
Data Loader with caching and fallback.
"""
import os
import pandas as pd
import requests
import structlog
from datetime import datetime, timedelta
from io import StringIO
from packages.strategy_foundry.configs.config import load_instrument_map

logger = structlog.get_logger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")

class DataLoader:
    def __init__(self):
        self.instrument_map = load_instrument_map()
        os.makedirs(CACHE_DIR, exist_ok=True)

    def get_data(self, instrument: str, timeframe: str, days: int = 60, force_refresh: bool = False) -> pd.DataFrame:
        """
        Get OHLCV data for instrument.
        Priority:
        1. Cache (if valid and !force_refresh)
        2. Yahoo Finance (Requests)
        """
        # Map instrument to symbol
        symbol = self.instrument_map.get("research", {}).get(instrument, instrument)

        cache_path = os.path.join(CACHE_DIR, f"{instrument}_{timeframe}.csv")

        if not force_refresh and os.path.exists(cache_path):
            # Check if cache is fresh enough (e.g. < 1 hour old for intraday, < 1 day for daily)
            # For now, just load if exists, hourly runner will force_refresh
            logger.info("Loading from cache", instrument=instrument, timeframe=timeframe)
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            return df

        logger.info("Fetching data", instrument=instrument, symbol=symbol, timeframe=timeframe)
        try:
            df = self._fetch_yahoo(symbol, timeframe, days)
            if not df.empty:
                df.to_csv(cache_path)
            return df
        except Exception as e:
            logger.error("Failed to fetch data", error=str(e))
            # Fallback to cache if available even if stale
            if os.path.exists(cache_path):
                logger.warning("Falling back to stale cache")
                return pd.read_csv(cache_path, index_col=0, parse_dates=True)
            return pd.DataFrame()

    def _fetch_yahoo(self, symbol: str, timeframe: str, days: int) -> pd.DataFrame:
        """
        Fetch from Yahoo Finance using requests.
        """
        # Interval mapping
        interval_map = {
            "5m": "5m",
            "15m": "15m",
            "1h": "60m",
            "1d": "1d"
        }
        interval = interval_map.get(timeframe, "1d")

        # Calculate period
        # Yahoo supports 'range' or 'period1'/'period2'
        # ranges: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        # For intraday (5m, 15m), max range is 60d.
        range_str = "60d"
        if timeframe == "1d":
            range_str = "5y" # Get enough history

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            "interval": interval,
            "range": range_str,
            "events": "history"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }

        resp = requests.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        try:
            result = data["chart"]["result"][0]
            timestamps = result["timestamp"]
            indicators = result["indicators"]["quote"][0]

            df = pd.DataFrame({
                "open": indicators["open"],
                "high": indicators["high"],
                "low": indicators["low"],
                "close": indicators["close"],
                "volume": indicators["volume"]
            }, index=pd.to_datetime(timestamps, unit="s", utc=True))

            # Convert to IST
            df.index = df.index.tz_convert("Asia/Kolkata")

            # Drop NaNs
            df.dropna(inplace=True)

            # Rename index
            df.index.name = "date"

            return df
        except (KeyError, IndexError) as e:
            logger.error("Error parsing Yahoo response", error=str(e))
            return pd.DataFrame()

if __name__ == "__main__":
    # Test
    loader = DataLoader()
    df = loader.get_data("NIFTY", "5m")
    print(df.tail())
