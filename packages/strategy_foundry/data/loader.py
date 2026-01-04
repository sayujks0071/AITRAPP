import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import structlog
from typing import Optional
from pathlib import Path

logger = structlog.get_logger(__name__)

CACHE_DIR = Path("packages/strategy_foundry/data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

SYMBOL_MAP = {
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN"
}

def load_instrument_data(symbol: str, lookback_days: int = 3650, force_refresh: bool = False) -> pd.DataFrame:
    """
    Load OHLCV data for an instrument (NIFTY/SENSEX).
    Prioritizes cache, downloads if stale or missing.
    """
    y_symbol = SYMBOL_MAP.get(symbol, symbol)
    cache_file = CACHE_DIR / f"{symbol}.csv"

    # Check cache
    if not force_refresh and cache_file.exists():
        # Check freshness (e.g. if updated today)
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if mtime.date() >= datetime.now().date():
             try:
                 df = pd.read_csv(cache_file, parse_dates=["Date"], index_col="Date")
                 logger.info("Loaded data from cache", symbol=symbol, rows=len(df))
                 return df
             except Exception as e:
                 logger.warning("Cache corrupted, re-downloading", symbol=symbol, error=str(e))

    # Download
    logger.info("Downloading data", symbol=symbol, source="Yahoo")
    df = _download_yahoo_data(y_symbol, lookback_days)

    if not df.empty:
        df.to_csv(cache_file)
        logger.info("Cached data", symbol=symbol, path=str(cache_file))

    return df

def _download_yahoo_data(symbol: str, days: int) -> pd.DataFrame:
    """
    Download data from Yahoo Finance Chart API.
    """
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=days)

    period1 = int(start_dt.timestamp())
    period2 = int(end_dt.timestamp())

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        "period1": period1,
        "period2": period2,
        "interval": "1d",
        "events": "history"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        indicators = result["indicators"]["quote"][0]

        df = pd.DataFrame({
            "Date": pd.to_datetime(timestamps, unit="s").tz_localize("UTC").tz_convert("Asia/Kolkata").normalize(),
            "open": indicators["open"],
            "high": indicators["high"],
            "low": indicators["low"],
            "close": indicators["close"],
            "volume": indicators["volume"]
        })

        df = df.set_index("Date").sort_index()
        # Drop rows with missing data
        df = df.dropna()

        return df

    except Exception as e:
        logger.error("Failed to download data", symbol=symbol, error=str(e))
        return pd.DataFrame()
