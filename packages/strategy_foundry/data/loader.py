import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict
import pandas as pd
import httpx
import structlog
import pytz
from io import StringIO

logger = structlog.get_logger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
IST = pytz.timezone("Asia/Kolkata")

INSTRUMENTS = {
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN"
}

def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_yahoo_data(symbol: str, period_days: int = 365 * 5) -> Optional[pd.DataFrame]:
    """
    Fetch daily data from Yahoo Finance.
    """
    try:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=period_days)

        period1 = int(start_dt.timestamp())
        period2 = int(end_dt.timestamp())

        url = f"https://query1.finance.yahoo.com/v7/finance/download/{symbol}"
        params = {
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true"
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }

        logger.info("Fetching data from Yahoo", symbol=symbol)
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params, headers=headers)
            response.raise_for_status()

            # Parse CSV
            df = pd.read_csv(StringIO(response.text))
            return df

    except Exception as e:
        logger.error("Failed to fetch data", symbol=symbol, error=str(e))
        return None

def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and clean OHLCV data.
    """
    required_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]

    # Check columns
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"Missing columns. Expected {required_cols}")

    # Standardize column names
    df = df.rename(columns={
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
        "Adj Close": "adj_close"
    })

    # Parse dates
    df["date"] = pd.to_datetime(df["date"])

    # Drop NaNs
    df = df.dropna()

    # Sort
    df = df.sort_values("date")

    # Sanity checks
    df = df[df["high"] >= df["low"]]
    df = df[df["high"] >= df["open"]]
    df = df[df["high"] >= df["close"]]
    df = df[df["low"] <= df["open"]]
    df = df[df["low"] <= df["close"]]
    df = df[df["volume"] >= 0]

    # Remove duplicates
    df = df.drop_duplicates(subset=["date"])

    # Localize to IST (assuming Yahoo daily dates are effectively market days)
    # We set 09:15 IST as the time for the daily bar start for consistency
    df["date"] = df["date"].dt.tz_localize(None).dt.tz_localize(IST) + timedelta(hours=9, minutes=15)

    df = df.set_index("date")
    return df

def get_data(symbol_key: str, force_refresh: bool = False) -> pd.DataFrame:
    """
    Get data for a symbol (NIFTY or SENSEX).
    Uses cache if available and fresh (< 24h).
    """
    if symbol_key not in INSTRUMENTS:
        raise ValueError(f"Unknown symbol: {symbol_key}")

    yahoo_symbol = INSTRUMENTS[symbol_key]
    cache_file = os.path.join(CACHE_DIR, f"{symbol_key}.csv")
    ensure_cache_dir()

    load_from_cache = False
    if os.path.exists(cache_file) and not force_refresh:
        # Check freshness
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime < 3600 * 12: # 12 hours freshness
            load_from_cache = True
            logger.info("Using cached data", symbol=symbol_key)

    if load_from_cache:
        try:
            df = pd.read_csv(cache_file)
            df["date"] = pd.to_datetime(df["date"])
            if df["date"].dt.tz is None:
                 df["date"] = df["date"].dt.tz_localize(IST)
            df = df.set_index("date")
            return df
        except Exception as e:
            logger.warn("Failed to read cache, fetching fresh", error=str(e))

    # Fetch fresh
    raw_df = fetch_yahoo_data(yahoo_symbol)
    if raw_df is None:
        if os.path.exists(cache_file):
            logger.warning("Download failed, using stale cache", symbol=symbol_key)
            df = pd.read_csv(cache_file)
            df["date"] = pd.to_datetime(df["date"])
            if df["date"].dt.tz is None:
                 df["date"] = df["date"].dt.tz_localize(IST)
            df = df.set_index("date")
            return df
        else:
            raise RuntimeError(f"Could not fetch data for {symbol_key} and no cache available")

    # Validate and clean
    clean_df = validate_data(raw_df)

    # Save to cache
    clean_df.to_csv(cache_file, index=False)
    logger.info("Cached data", symbol=symbol_key, rows=len(clean_df))

    return clean_df

def get_all_data() -> Dict[str, pd.DataFrame]:
    """Get data for all supported instruments"""
    data = {}
    for key in INSTRUMENTS:
        try:
            data[key] = get_data(key)
        except Exception as e:
            logger.error("Skipping instrument due to error", symbol=key, error=str(e))
    return data
