import pandas as pd
import httpx
import time
from pathlib import Path
from datetime import datetime, timezone
import structlog
import io
import random

logger = structlog.get_logger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

YAHOO_URL = "https://query1.finance.yahoo.com/v7/finance/download/{symbol}"

MAPPING = {
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN"
}

def load_data(instrument: str, days_back: int = 2000) -> pd.DataFrame:
    """
    Load data for instrument (NIFTY/SENSEX).
    Tries cache first. If stale (> 24h) or missing, downloads.
    """
    symbol = MAPPING.get(instrument, instrument)
    cache_path = CACHE_DIR / f"{instrument}.csv"

    # Check cache
    if cache_path.exists():
        mtime = cache_path.stat().st_mtime
        if time.time() - mtime < 3600 * 4: # 4 hours cache validity
             try:
                 df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                 logger.info("Loaded from cache", instrument=instrument)
                 return df
             except Exception:
                 logger.warning("Cache corrupt, redownloading", instrument=instrument)

    # Download
    logger.info("Downloading data", instrument=instrument, symbol=symbol)
    df = _download_yahoo(symbol, days_back)

    # Normalize
    if not df.empty:
        # Save to cache
        df.to_csv(cache_path)
    else:
        # Fallback for dev/test environments if Yahoo blocks
        if days_back < 5000: # Heuristic to detect if we can fallback to dummy
             logger.warning("Using dummy data fallback due to download failure")
             from .dummy import generate_dummy_data
             df = generate_dummy_data()
             df.to_csv(cache_path)

    return df

def _download_yahoo(symbol: str, days_back: int) -> pd.DataFrame:
    end_ts = int(time.time())
    start_ts = end_ts - (days_back * 86400)

    params = {
        "period1": start_ts,
        "period2": end_ts,
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true"
    }

    # Random User Agent to avoid 429
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36"
    ]

    headers = {
        "User-Agent": random.choice(user_agents)
    }

    try:
        url = YAHOO_URL.format(symbol=symbol)
        with httpx.Client() as client:
            resp = client.get(url, params=params, headers=headers, follow_redirects=True)
            resp.raise_for_status()

        df = pd.read_csv(io.BytesIO(resp.content))

        # Yahoo columns: Date, Open, High, Low, Close, Adj Close, Volume
        df = df.rename(columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        })

        # Drop Adj Close if exists
        if "Adj Close" in df.columns:
            df = df.drop(columns=["Adj Close"])

        # Parse dates
        df["date"] = pd.to_datetime(df["date"])

        # Set index
        df = df.set_index("date").sort_index()

        # Handle timezone: assume source is market local (IST for NIFTY/SENSEX)
        # We localize to Asia/Kolkata
        # If dates are just dates (00:00:00), we localize them
        df.index = df.index.tz_localize("Asia/Kolkata")

        # Numeric conversion
        cols = ["open", "high", "low", "close", "volume"]
        for c in cols:
            df[c] = pd.to_numeric(df[c], errors='coerce')

        df = df.dropna()

        return df

    except Exception as e:
        logger.error("Download failed", symbol=symbol, error=str(e))
        return pd.DataFrame()

def update_cache():
    for instr in MAPPING.keys():
        load_data(instr, days_back=3000)
