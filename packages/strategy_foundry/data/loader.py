import os
import pandas as pd
import requests
import logging
from datetime import datetime, timedelta
from io import StringIO
import pytz

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
YAHOO_URL = "https://query1.finance.yahoo.com/v7/finance/download/{symbol}?period1={start}&period2={end}&interval=1d&events=history&includeAdjustedClose=true"

INSTRUMENT_MAP = {
    'NIFTY': '^NSEI',
    'SENSEX': '^BSESN'
}

class DataLoader:
    def __init__(self, cache_dir=CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, symbol):
        return os.path.join(self.cache_dir, f"{symbol}.csv")

    def download_data(self, symbol, days=365*5):
        """Downloads data from Yahoo Finance."""
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)

        # Yahoo expects unix timestamp
        period1 = int(start_dt.timestamp())
        period2 = int(end_dt.timestamp())

        yahoo_symbol = INSTRUMENT_MAP.get(symbol, symbol)
        url = YAHOO_URL.format(symbol=yahoo_symbol, start=period1, end=period2)

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }

        try:
            logger.info(f"Downloading {symbol} from {url}")
            response = requests.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()

            df = pd.read_csv(StringIO(response.text))

            # Normalize columns
            df.columns = [c.lower() for c in df.columns]
            df.rename(columns={'date': 'datetime'}, inplace=True)

            # Parse dates
            df['datetime'] = pd.to_datetime(df['datetime'])

            # Drop NaN
            df.dropna(inplace=True)

            return df
        except Exception as e:
            logger.error(f"Failed to download {symbol}: {e}")
            return None

    def get_data(self, symbol, force_download=False):
        """Gets data from cache or downloads it."""
        cache_path = self._get_cache_path(symbol)

        # Check cache validity (simple check: if exists and modified today)
        is_cached = os.path.exists(cache_path)
        is_fresh = False
        if is_cached:
            mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
            if datetime.now() - mtime < timedelta(hours=12):
                is_fresh = True

        if is_cached and is_fresh and not force_download:
            logger.info(f"Loading {symbol} from cache")
            df = pd.read_csv(cache_path)
        else:
            df = self.download_data(symbol)
            if df is not None:
                # Save to cache
                df.to_csv(cache_path, index=False)
            elif is_cached:
                 # Fallback to stale cache if download fails
                logger.warning(f"Download failed, falling back to stale cache for {symbol}")
                df = pd.read_csv(cache_path)
            else:
                raise ValueError(f"No data available for {symbol}")

        # Standardize columns if loaded from cache (e.g. date -> datetime)
        df.columns = [c.lower() for c in df.columns]
        if 'date' in df.columns and 'datetime' not in df.columns:
            df.rename(columns={'date': 'datetime'}, inplace=True)

        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        else:
            raise ValueError(f"Data for {symbol} missing 'datetime' or 'date' column")

        df.sort_values('datetime', inplace=True)
        df.reset_index(drop=True, inplace=True)

        return df

if __name__ == "__main__":
    loader = DataLoader()
    try:
        df = loader.get_data("NIFTY")
        print(df.tail())
    except Exception as e:
        print(e)
