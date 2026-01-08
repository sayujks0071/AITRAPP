"""
Data Loader for NIFTY/SENSEX.
Fetches from Yahoo Finance via requests, caches to CSV.
"""
import os
import csv
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)

CACHE_DIR = "packages/strategy_foundry/data/cache"
MAPPINGS = {
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN"
}

def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def fetch_yahoo_data(symbol: str, period1: int, period2: int) -> Optional[str]:
    """
    Fetch CSV data from Yahoo Finance.
    """
    url = f"https://query1.finance.yahoo.com/v7/finance/download/{symbol}?period1={period1}&period2={period2}&interval=1d&events=history&includeAdjustedClose=true"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    }
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.text
        else:
            logger.error("Failed to fetch data", symbol=symbol, status=resp.status_code)
            return None
    except Exception as e:
        logger.error("Error fetching data", symbol=symbol, error=str(e))
        return None

def load_instrument(name: str, force_refresh: bool = False) -> pd.DataFrame:
    """
    Load instrument data (NIFTY/SENSEX).
    Returns DataFrame with [open, high, low, close, volume] and DateTimeIndex in IST.
    """
    ensure_cache_dir()
    y_symbol = MAPPINGS.get(name)
    if not y_symbol:
        raise ValueError(f"Unknown instrument: {name}")

    cache_file = os.path.join(CACHE_DIR, f"{name}.csv")

    # Check if cache exists and is fresh (e.g. < 24h old)
    is_stale = True
    if os.path.exists(cache_file):
        mtime = os.path.getmtime(cache_file)
        if (datetime.now().timestamp() - mtime) < 86400: # 24 hours
            is_stale = False

    if force_refresh or is_stale:
        logger.info("Downloading data", instrument=name)
        # Download last 10 years
        end = int(datetime.now().timestamp())
        start = int((datetime.now() - timedelta(days=365*10)).timestamp())

        csv_text = fetch_yahoo_data(y_symbol, start, end)
        if csv_text:
            with open(cache_file, "w") as f:
                f.write(csv_text)
        else:
            logger.warning("Using stale data if available")

    if not os.path.exists(cache_file):
        raise FileNotFoundError(f"No data found for {name}")

    df = pd.read_csv(cache_file)

    # Clean and standardize
    df.columns = [c.lower() for c in df.columns]
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

    # Standard columns
    cols = ['open', 'high', 'low', 'close', 'volume']
    df = df[cols].copy()

    # Fill NAs
    df.ffill(inplace=True)

    # Set timezone
    # Yahoo data is typically local time without tz. For NSE, it's IST.
    # We will localize.
    if df.index.tz is None:
        df.index = df.index.tz_localize("Asia/Kolkata")
    else:
        df.index = df.index.tz_convert("Asia/Kolkata")

    return df
