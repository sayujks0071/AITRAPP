import os
import requests
import pandas as pd
import io
import time
from datetime import datetime, timedelta
import pytz
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)

CACHE_DIR = Path("packages/strategy_foundry/data/cache")
YAHOO_URL = "https://query1.finance.yahoo.com/v7/finance/download/{symbol}"

class DataLoader:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.tz = pytz.timezone("Asia/Kolkata")

    def get_data(self, symbol: str, force_download: bool = False) -> pd.DataFrame:
        """
        Get daily OHLCV data for a symbol.
        1. Check cache (today's data must be present if market closed, or just recent enough).
           Actually, for strategy foundry, we usually run on closed bars.
           We'll cache by date.
        2. Download if missing or forced.
        3. Returns DataFrame with DatetimeIndex (Asia/Kolkata).
        """
        file_path = self.cache_dir / f"{symbol}.csv"

        # Determine if we need to download
        need_download = force_download
        if not file_path.exists():
            need_download = True
        else:
            # Check if cache is stale (older than 12 hours)
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if datetime.now() - mtime > timedelta(hours=12):
                need_download = True

        df = None
        if need_download:
            try:
                logger.info(f"Downloading data for {symbol}")
                df = self._download_yahoo(symbol)
                df.to_csv(file_path)
            except Exception as e:
                logger.error(f"Failed to download {symbol}: {e}")
                if file_path.exists():
                    logger.info(f"Falling back to cached data for {symbol}")
                    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                else:
                    raise e
        else:
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)

        return self._process_dataframe(df)

    def _download_yahoo(self, symbol: str) -> pd.DataFrame:
        # Download last 5 years
        end_dt = int(time.time())
        start_dt = int((datetime.now() - timedelta(days=365*5)).timestamp())

        params = {
            "period1": start_dt,
            "period2": end_dt,
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true"
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }

        url = YAHOO_URL.format(symbol=symbol)
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()

        df = pd.read_csv(io.StringIO(resp.text), index_col="Date", parse_dates=True)
        return df

    def _process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        # Standardize columns
        df.columns = [c.lower() for c in df.columns]
        # Rename adjusted close if needed, but usually we use Close.
        # Yahoo gives: Date, Open, High, Low, Close, Adj Close, Volume

        if "adj close" in df.columns:
            # We prefer Adj Close for backtesting to handle splits/dividends roughly,
            # but for live consistency 'Close' is often better if we don't have adjusted live feed.
            # However, for pure backtest lab, Adj Close is safer for returns.
            # Let's map Close -> Open/High/Low adjustment? No, that's complex.
            # Simple approach: Use Close.
            pass

        required = ["open", "high", "low", "close", "volume"]
        df = df[required].copy()

        # Drop NaNs
        df.dropna(inplace=True)

        # Sort index
        df.sort_index(inplace=True)

        # Localize/Convert timezone
        # Yahoo dates are typically just dates (YYYY-MM-DD). Pandas parses them as 00:00:00.
        # We assume they are representative of the session.
        # For India, we can localize to Asia/Kolkata
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert(self.tz)
        else:
            df.index = df.index.tz_convert(self.tz)

        return df

    def get_nifty(self) -> pd.DataFrame:
        return self.get_data("^NSEI")

    def get_sensex(self) -> pd.DataFrame:
        return self.get_data("^BSESN")
