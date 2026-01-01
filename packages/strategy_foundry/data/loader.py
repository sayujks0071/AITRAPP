"""Data Loader for Strategy Foundry"""
import os
import requests
import pandas as pd
from io import StringIO
from datetime import datetime
import logging
import pytz

logger = logging.getLogger(__name__)

CACHE_DIR = "packages/strategy_foundry/data/cache"
IST = pytz.timezone("Asia/Kolkata")

class DataLoader:
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_history(self, symbol: str, days: int = 2520) -> pd.DataFrame:
        """
        Get historical data for a symbol.
        1. Check cache.
        2. If missing or stale (today's data missing), fetch from Yahoo.
        """
        # Symbol cleanup for filenames (e.g. ^NSEI -> NSEI)
        safe_symbol = symbol.replace("^", "")
        cache_path = os.path.join(self.cache_dir, f"{safe_symbol}.csv")

        df = None
        if os.path.exists(cache_path):
            try:
                df = pd.read_csv(cache_path, parse_dates=["Date"], index_col="Date")
                # Normalize timezone
                if df.index.tz is None:
                    df.index = df.index.tz_localize("UTC").tz_convert(IST)

                # Check staleness
                last_date = df.index[-1].date()
                today = datetime.now(IST).date()

                # If market is open or we are same day, we might be stale,
                # but for daily bars, we usually update once a day after close.
                # Simplification: if last data is not today, try to update.
                if last_date < today:
                    logger.info(f"Data stale for {symbol}, refreshing...")
                    df = self._download_and_cache(symbol, cache_path)
                else:
                    logger.info(f"Using cached data for {symbol}")

            except Exception as e:
                logger.warning(f"Failed to load cache for {symbol}: {e}")
                df = self._download_and_cache(symbol, cache_path)
        else:
            logger.info(f"Cache miss for {symbol}, downloading...")
            df = self._download_and_cache(symbol, cache_path)

        return df

    def _download_and_cache(self, symbol: str, cache_path: str) -> pd.DataFrame:
        try:
            # Yahoo Finance download
            # period1 = start, period2 = end (now)
            end_ts = int(datetime.now().timestamp())
            start_ts = int((datetime.now() - pd.Timedelta(days=365*10)).timestamp()) # 10 years

            url = f"https://query1.finance.yahoo.com/v7/finance/download/{symbol}?period1={start_ts}&period2={end_ts}&interval=1d&events=history"
            headers = {'User-Agent': 'Mozilla/5.0'}

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            csv_data = StringIO(response.text)
            df = pd.read_csv(csv_data, parse_dates=["Date"], index_col="Date")

            # Clean up
            df = df.dropna()

            # Timezone handling: Yahoo is usually UTC-adjusted for daily, or exchange local time?
            # Yahoo daily bars are typically exchange local time but with 00:00:00.
            # Let's assume they are exchange local (IST for NSE).
            # But pd.read_csv makes them naive. We localize to IST.
            if df.index.tz is None:
                df.index = df.index.tz_localize(IST)

            # Save to cache
            df.to_csv(cache_path)

            return df

        except Exception as e:
            logger.error(f"Failed to download {symbol}: {e}")
            # Return empty DF or raise
            if os.path.exists(cache_path):
                 # Fallback to whatever we have if download fails
                 return pd.read_csv(cache_path, parse_dates=["Date"], index_col="Date")
            raise e
