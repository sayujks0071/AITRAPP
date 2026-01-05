"""
Data loader for Strategy Foundry.
Fetches daily data from Yahoo Finance via requests.
Caches to CSV.
"""
import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import structlog
from pathlib import Path
import io

logger = structlog.get_logger(__name__)

CACHE_DIR = Path("packages/strategy_foundry/data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Symbol Mapping
SYMBOLS = {
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN"
}

def fetch_data(symbol_key: str, days: int = 365*5) -> pd.DataFrame:
    """
    Fetch daily OHLCV data for symbol.

    Args:
        symbol_key: 'NIFTY' or 'SENSEX'
        days: Number of days of history to fetch

    Returns:
        DataFrame with index Date (tz-aware Asia/Kolkata) and columns: open, high, low, close, volume
    """
    ticker = SYMBOLS.get(symbol_key)
    if not ticker:
        raise ValueError(f"Unknown symbol: {symbol_key}")

    # Check cache first
    cache_file = CACHE_DIR / f"{symbol_key}.csv"
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Simple cache invalidation: if file modified today, use it.
    # Actually, we want fresh data if market is open or closed recently.
    # For now, let's fetch fresh if cache is older than 12 hours.

    force_refresh = False
    if cache_file.exists():
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - mtime > timedelta(hours=12):
            force_refresh = True
    else:
        force_refresh = True

    if not force_refresh:
        try:
            logger.info("Loading from cache", symbol=symbol_key)
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            if not df.index.tz:
                 df.index = df.index.tz_localize("Asia/Kolkata")
            return df
        except Exception as e:
            logger.warning("Cache load failed, fetching fresh", error=str(e))

    # Download from Yahoo
    # Calculate period1 and period2
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=days)

    period1 = int(start_dt.timestamp())
    period2 = int(end_dt.timestamp())

    url = f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}?period1={period1}&period2={period2}&interval=1d&events=history&includeAdjustedClose=true"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    }

    try:
        logger.info("Downloading data", symbol=symbol_key, url=url)
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        df = pd.read_csv(io.StringIO(response.text), index_col="Date", parse_dates=True)

        # Clean up
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        df.columns = ["open", "high", "low", "close", "volume"]

        # Drop missing
        df.dropna(inplace=True)

        # Normalize Index to Asia/Kolkata
        # Yahoo dates are typically YYYY-MM-DD representing local market time.
        # We need to make them tz-aware.
        if df.index.tz is None:
             df.index = df.index.tz_localize("Asia/Kolkata")
        else:
             df.index = df.index.tz_convert("Asia/Kolkata")

        # Sort
        df.sort_index(inplace=True)

        # Save to cache
        df.to_csv(cache_file)

        return df

    except Exception as e:
        logger.error("Download failed", error=str(e))
        # Try fallback to cache if available even if stale
        if cache_file.exists():
            return pd.read_csv(cache_file, index_col=0, parse_dates=True)
        raise

def get_latest_price(symbol_key: str) -> float:
    df = fetch_data(symbol_key, days=5)
    return df['close'].iloc[-1]
