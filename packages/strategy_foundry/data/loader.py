import pandas as pd
from typing import Dict, Optional, List
import requests
import os
from datetime import datetime
import io
import pytz

CACHE_DIR = "packages/strategy_foundry/data/cache"
IST = pytz.timezone("Asia/Kolkata")

# Symbol Map
SYMBOL_MAP = {
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN"
}

def load_data(symbol: str, lookback_days: int = 365*2) -> pd.DataFrame:
    """
    Load data for a symbol (NIFTY/SENSEX).
    Checks cache first, then downloads if stale/missing.
    Returns DataFrame with Index=Date (IST), columns=[open, high, low, close, volume]
    """
    y_symbol = SYMBOL_MAP.get(symbol, symbol)
    cache_path = os.path.join(CACHE_DIR, f"{symbol}.csv")

    df = _load_from_cache(cache_path)
    if df is not None and _is_fresh(df):
        return df

    # Download
    print(f"Downloading fresh data for {symbol}...")
    df = _download_yahoo(y_symbol, lookback_days)
    if df is not None:
        # Save to cache
        os.makedirs(CACHE_DIR, exist_ok=True)
        df.to_csv(cache_path)
    elif df is None and os.path.exists(cache_path):
        # Fallback to cache if download fails
        print(f"Download failed, using stale cache for {symbol}")
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)

    # Ensure Index is tz-aware (IST) if not already
    if df is not None and not df.empty:
         if df.index.tz is None:
             # Yahoo daily is usually just date.
             # We can assume it represents 00:00 or market open.
             # Let's normalize to UTC first if unsure, but usually date is date.
             # If we just localize, 00:00 becomes 00:00 IST.
             df.index = df.index.tz_localize("UTC").tz_convert(IST)

    return df

def _load_from_cache(path: str) -> Optional[pd.DataFrame]:
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        return df
    except Exception:
        return None

def _is_fresh(df: pd.DataFrame) -> bool:
    if df.empty:
        return False
    last_date = df.index[-1]

    # If tz-aware, compare with now(tz)
    now = datetime.now(IST) if last_date.tzinfo else datetime.now()

    # Simple check: if last date is today or yesterday
    delta = now - last_date
    return delta.days < 3

def _download_yahoo(symbol: str, days: int) -> Optional[pd.DataFrame]:
    """
    Download from Yahoo Finance v8 endpoint using requests.
    """
    try:
        # Yahoo requires period1 and period2 in unix timestamp
        end = int(datetime.now().timestamp())
        start = int((datetime.now() - pd.Timedelta(days=days)).timestamp())

        url = f"https://query1.finance.yahoo.com/v7/finance/download/{symbol}?period1={start}&period2={end}&interval=1d&events=history&includeAdjustedClose=true"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Failed to download {symbol}: {response.status_code}")
            return None

        df = pd.read_csv(io.StringIO(response.text), parse_dates=['Date'], index_col='Date')

        # Normalize columns
        df.columns = [c.lower() for c in df.columns]
        # Keep OHLCV
        cols = ['open', 'high', 'low', 'close', 'volume']

        df = df[cols].copy()

        # Drop NaNs
        df.dropna(inplace=True)

        return df
    except Exception as e:
        print(f"Error downloading {symbol}: {e}")
        return None
