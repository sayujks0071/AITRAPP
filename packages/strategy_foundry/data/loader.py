import logging
import os
import time
from datetime import datetime, timedelta
from io import StringIO

import pandas as pd
import requests

logger = logging.getLogger(__name__)

class DataLoader:
    """
    Downloads and caches historical market data from Yahoo Finance.
    Focus: Daily data for NIFTY (^NSEI) and SENSEX (^BSESN).
    """

    BASE_URL = "https://query1.finance.yahoo.com/v7/finance/download/{symbol}"

    def __init__(self, cache_dir="packages/strategy_foundry/data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        self.symbol_map = {
            "NIFTY": "^NSEI",
            "SENSEX": "^BSESN"
        }

    def fetch_data(self, instrument: str, force_refresh: bool = False) -> pd.DataFrame:
        """
        Fetch Daily OHLCV data for the given instrument.

        Args:
            instrument: "NIFTY" or "SENSEX"
            force_refresh: If True, ignore cache and download fresh

        Returns:
            pd.DataFrame with DatetimeIndex (Asia/Kolkata), columns: open, high, low, close, volume
        """
        symbol = self.symbol_map.get(instrument, instrument)
        cache_path = os.path.join(self.cache_dir, f"{instrument}_1D.csv")

        # 1. Try Cache
        if not force_refresh and os.path.exists(cache_path):
            try:
                logger.info(f"Loading {instrument} from cache: {cache_path}")
                df = pd.read_csv(cache_path, index_col="Date", parse_dates=True)
                # Ensure index is tz-aware if not already
                if df.index.tz is None:
                    df.index = df.index.tz_localize("Asia/Kolkata")
                else:
                    df.index = df.index.tz_convert("Asia/Kolkata")
                return df
            except Exception as e:
                logger.warning(f"Failed to load cache for {instrument}: {e}")

        # 2. Download
        logger.info(f"Downloading {instrument} ({symbol}) from Yahoo...")
        df = self._download_yahoo_daily(symbol)

        if df is not None and not df.empty:
            # 3. Save Cache
            df.to_csv(cache_path)
            return df

        # 4. Fallback: Return empty or old cache if download failed
        if os.path.exists(cache_path):
            logger.warning("Download failed, returning stale cache.")
            return pd.read_csv(cache_path, index_col="Date", parse_dates=True)

        return pd.DataFrame()

    def _download_yahoo_daily(self, symbol: str) -> pd.DataFrame:
        """
        Download daily data using requests.
        """
        # Range: 10 years
        period1 = int((datetime.now() - timedelta(days=365*10)).timestamp())
        period2 = int(datetime.now().timestamp())

        params = {
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true"
        }

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        url = self.BASE_URL.format(symbol=symbol)

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            # Parse CSV
            df = pd.read_csv(StringIO(response.text), index_col="Date", parse_dates=True)

            # Rename columns to lowercase
            df.rename(columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume"
            }, inplace=True)

            # Use Adj Close for Close to handle splits/dividends if desired?
            # Standard practice often uses Close for signals but Adj Close for returns.
            # Let's keep Close as is for now, or use Adj Close?
            # Strategy Foundry usually prefers raw price action for levels, but adjusted for returns.
            # However, Yahoo's "Close" is raw, "Adj Close" is split/div adjusted.
            # For simplicity and level-accuracy (e.g. psychological 20k), we use Close.
            # But for long backtests, Adj Close is better.
            # The prompt says "no magic". Let's stick to standard Close but maybe warn?
            # Actually, Yahoo's 'Close' is split adjusted but not dividend adjusted usually?
            # Let's just use the columns as is, dropping 'adj_close' to keep schema clean.

            cols = ["open", "high", "low", "close", "volume"]
            df = df[cols]

            # Handle missing values
            df.dropna(inplace=True)

            # Set Timezone
            # Yahoo daily dates are usually just dates (00:00 UTC or Local).
            # We treat them as 00:00 Asia/Kolkata for the "Day".
            # Or better, just localize to Asia/Kolkata
            df.index = df.index.tz_localize("UTC").tz_convert("Asia/Kolkata")

            # Filter bad data (Volume=0 can happen on holidays)
            df = df[df["volume"] > 0]

            return df

        except Exception as e:
            logger.error(f"Error downloading {symbol}: {e}")
            return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loader = DataLoader()
    df = loader.fetch_data("NIFTY")
    print(df.tail())
