"""
Data loader for StrategyFoundry.
Fetches daily history for NIFTY (^NSEI) and SENSEX (^BSESN) from Yahoo Finance.
Caches data in CSV format to avoid redundant downloads.
"""
import os
import csv
import io
import time
import requests
import logging
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Map instrument names to Yahoo tickers
TICKERS = {
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN"
}

# Standard column names
COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]

def get_data_path(instrument: str) -> Path:
    """Get path to cached CSV file."""
    return CACHE_DIR / f"{instrument}.csv"

def fetch_yahoo_history(ticker: str, start_date: str = None) -> str:
    """
    Fetch historical data from Yahoo Finance as CSV string.
    Uses period1/period2 parameters.
    """
    if start_date:
        start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
    else:
        # Default to 5 years ago
        start_ts = int((datetime.now() - timedelta(days=5*365)).timestamp())

    end_ts = int(datetime.now().timestamp())

    # URL construction
    # Note: Yahoo changed their API, but query1.finance.yahoo.com/v7/finance/download/ usually works with cookies
    # or simple requests often work for download endpoints if not heavily blocked.
    # Fallback to query2 if query1 fails.

    # A simple reliable way for public tickers often involves setting a User-Agent

    url = f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}"
    params = {
        "period1": start_ts,
        "period2": end_ts,
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }

    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()

    return response.text

def normalize_data(csv_text: str) -> pd.DataFrame:
    """
    Parse CSV text, normalize columns and timezone.
    """
    df = pd.read_csv(io.StringIO(csv_text))

    # Ensure columns exist
    for col in COLUMNS:
        if col not in df.columns:
            # Maybe differnet case?
            found = False
            for c in df.columns:
                if c.lower() == col.lower().replace(" ", ""):
                    df.rename(columns={c: col}, inplace=True)
                    found = True
                    break
            if not found:
                # If Volume is missing (some indices), fill 0
                if col == "Volume":
                    df["Volume"] = 0
                else:
                    raise ValueError(f"Missing column {col} in data")

    # Parse dates
    df["Date"] = pd.to_datetime(df["Date"])

    # Sort
    df.sort_values("Date", inplace=True)

    # Drop rows with NaN in OHLC
    df.dropna(subset=["Open", "High", "Low", "Close"], inplace=True)

    # Localize to IST
    # Yahoo dates are usually naive, effectively market local time (IST for NSE/BSE)
    # We will localize to Asia/Kolkata
    df["Date"] = df["Date"].dt.tz_localize("Asia/Kolkata", ambiguous='NaT', nonexistent='shift_forward')

    # Set index
    df.set_index("Date", inplace=True)

    return df

def load_instrument_data(instrument: str, force_download: bool = False) -> pd.DataFrame:
    """
    Load data for instrument.
    1. Check cache.
    2. If missing or stale (older than 18 hours) or force_download, fetch.
    3. Return DataFrame.
    """
    if instrument not in TICKERS:
        raise ValueError(f"Unknown instrument: {instrument}")

    ticker = TICKERS[instrument]
    path = get_data_path(instrument)

    needs_download = force_download

    if not path.exists():
        needs_download = True
    else:
        # Check if stale (file modified > 18 hours ago)
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        if datetime.now() - mtime > timedelta(hours=18):
            needs_download = True

    if needs_download:
        try:
            logger.info(f"Downloading data for {instrument} ({ticker})...")
            csv_text = fetch_yahoo_history(ticker)
            # Validate before saving
            df = normalize_data(csv_text)

            if df.empty:
                 logger.warning(f"Downloaded data for {instrument} is empty.")
            else:
                # Save to cache
                df.to_csv(path)
                logger.info(f"Saved {len(df)} rows to {path}")
                return df
        except Exception as e:
            logger.error(f"Failed to download {instrument}: {e}")
            if not path.exists():
                raise
            logger.info("Falling back to cached data.")

    # Load from cache
    logger.info(f"Loading {instrument} from cache...")
    df = pd.read_csv(path, index_col="Date", parse_dates=True)

    # Ensure index is timezone aware if read from CSV (CSV loses tz usually)
    if df.index.tz is None:
        df.index = df.index.tz_localize("Asia/Kolkata")

    return df

if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    try:
        df = load_instrument_data("NIFTY")
        print(df.tail())
    except Exception as e:
        print(f"Error: {e}")
