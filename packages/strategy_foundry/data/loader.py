import os
import csv
import time
from datetime import datetime, timedelta
import requests
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

SYMBOL_MAP = {
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN"
}

def get_historical_data(symbol: str, days: int = 3650) -> pd.DataFrame:
    """
    Get historical daily data for a symbol (NIFTY or SENSEX).
    Checks cache first, then downloads from Yahoo Finance.
    Returns DataFrame with Index=Date (Asia/Kolkata) and columns: open, high, low, close, volume.
    """
    symbol_yahoo = SYMBOL_MAP.get(symbol, symbol)
    cache_file = os.path.join(CACHE_DIR, f"{symbol}.csv")

    needs_download = True
    if os.path.exists(cache_file):
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime < 4 * 3600: # 4 hours
            needs_download = False

    df = None
    if not needs_download:
        try:
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            logger.info("Loaded from cache", symbol=symbol, rows=len(df))
        except Exception:
            needs_download = True

    if needs_download:
        logger.info("Downloading fresh data", symbol=symbol)
        try:
            df = download_yahoo_data(symbol_yahoo, days)
            df.to_csv(cache_file)
        except Exception as e:
            logger.error("Download failed, trying cache fallback", error=str(e))
            if os.path.exists(cache_file):
                df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            else:
                raise

    # Normalize
    if df is not None:
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert("Asia/Kolkata")
        else:
            df.index = df.index.tz_convert("Asia/Kolkata")

        required = ['open', 'high', 'low', 'close', 'volume']
        if not all(c in df.columns for c in required):
            raise ValueError(f"Missing columns in data: {df.columns}")

    return df

def download_yahoo_data(ticker: str, days: int) -> pd.DataFrame:
    """
    Download data from Yahoo Finance.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    period1 = int(start_date.timestamp())
    period2 = int(end_date.timestamp())

    url = f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}?period1={period1}&period2={period2}&interval=1d&events=history"

    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    from io import StringIO
    csv_data = StringIO(response.text)
    df = pd.read_csv(csv_data, index_col=0, parse_dates=True)

    df.columns = [c.lower() for c in df.columns]
    df = df[['open', 'high', 'low', 'close', 'volume']]
    df = df.dropna()

    for c in ['open', 'high', 'low', 'close']:
        df[c] = df[c].astype(float)

    return df
