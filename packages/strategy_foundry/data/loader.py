import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import structlog
import io

logger = structlog.get_logger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
# Ensure cache dir exists
os.makedirs(CACHE_DIR, exist_ok=True)

YAHOO_MAP = {
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN"
}

def get_data(symbol: str, lookback_days: int = 2000, force_refresh: bool = False) -> pd.DataFrame:
    """
    Get OHLCV data for symbol.
    1. Try cache.
    2. If stale or missing, download from Yahoo.
    3. Normalize.
    """
    yahoo_symbol = YAHOO_MAP.get(symbol, symbol)
    cache_path = os.path.join(CACHE_DIR, f"{symbol}.csv")

    # Check cache
    if not force_refresh and os.path.exists(cache_path):
        modified_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        # If cache is from today (and market closed or currently trading), we might want to refresh?
        # For simple daily backtest, if cache is less than 12 hours old, we stick with it.
        if datetime.now() - modified_time < timedelta(hours=4):
            logger.info(f"Loading {symbol} from cache")
            try:
                df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
                return _normalize(df)
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")

    # Download
    logger.info(f"Downloading {symbol} from Yahoo")
    try:
        df = _download_yahoo(yahoo_symbol, lookback_days)
        if not df.empty:
            df.to_csv(cache_path)
            return _normalize(df)
    except Exception as e:
        logger.error(f"Failed to download {symbol}: {e}")
        # Fallback to cache if exists
        if os.path.exists(cache_path):
            logger.warning("Falling back to stale cache")
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            return _normalize(df)

    return pd.DataFrame()

def _download_yahoo(symbol: str, lookback_days: int) -> pd.DataFrame:
    end = int(time.time())
    start = int((datetime.now() - timedelta(days=lookback_days)).timestamp())

    url = f"https://query1.finance.yahoo.com/v7/finance/download/{symbol}"
    params = {
        "period1": start,
        "period2": end,
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }

    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()

    df = pd.read_csv(io.StringIO(response.text))
    return df

def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize columns and index.
    """
    # Standardize columns
    df.columns = [c.lower().replace(" ", "") for c in df.columns]

    # Ensure Date index
    if 'date' in df.columns:
        df.set_index('date', inplace=True)

    df.index = pd.to_datetime(df.index, utc=True)

    # Convert to Asia/Kolkata
    df.index = df.index.tz_convert("Asia/Kolkata")

    # Drop rows with NaN
    df.dropna(inplace=True)

    # Ensure required columns
    required = {'open', 'high', 'low', 'close', 'volume'}
    if not required.issubset(df.columns):
        # Adjust close might be present
        if 'adjclose' in df.columns:
             # Use adjclose as close if preferred, but for now stick to Close
             pass
        raise ValueError(f"Missing columns: {required - set(df.columns)}")

    return df[['open', 'high', 'low', 'close', 'volume']].sort_index()

if __name__ == "__main__":
    # Test
    df = get_data("NIFTY", lookback_days=30)
    print(df.tail())
