import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

CACHE_DIR = "packages/strategy_foundry/data/cache"
YAHOO_URL = "https://query1.finance.yahoo.com/v7/finance/download/{symbol}"

# Map internal symbols to Yahoo symbols
SYMBOL_MAP = {
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN"
}

class DataLoader:
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, symbol: str) -> str:
        return os.path.join(self.cache_dir, f"{symbol}.csv")

    def download_data(self, symbol: str, days: int = 3650) -> Optional[pd.DataFrame]:
        """Download data from Yahoo Finance"""
        yahoo_symbol = SYMBOL_MAP.get(symbol, symbol)

        end_date = int(time.time())
        start_date = int((datetime.now() - timedelta(days=days)).timestamp())

        params = {
            "period1": start_date,
            "period2": end_date,
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true"
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }

        url = YAHOO_URL.format(symbol=yahoo_symbol)

        try:
            logger.info("Downloading data", symbol=symbol, url=url)
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 429:
                 logger.error("Rate limited by Yahoo Finance (429)", symbol=symbol)
                 return None

            response.raise_for_status()

            temp_path = self._get_cache_path(symbol) + ".tmp"
            with open(temp_path, "wb") as f:
                f.write(response.content)

            df = pd.read_csv(temp_path)
            os.remove(temp_path)
            return df

        except Exception as e:
            logger.error("Failed to download data", symbol=symbol, error=str(e))
            return None

    def _extract_from_seed(self, symbol: str) -> Optional[pd.DataFrame]:
        """Extract underlying data from core option files if available"""
        if symbol != "NIFTY":
            return None

        seed_path = "docs/NSE OPINONS DATA/OPTIDX_NIFTY_CE_12-Aug-2025_TO_12-Nov-2025.csv"
        if not os.path.exists(seed_path):
            return None

        try:
            logger.info("Extracting seed data from options chain", path=seed_path)
            df = pd.read_csv(seed_path)
            # Group by Date and take the first Underlying Value
            # Columns: Date, Underlying Value
            # Date format: 12-Nov-2025

            # Clean columns
            df.columns = [c.strip() for c in df.columns]

            daily = df.groupby("Date")["Underlying Value"].first().reset_index()
            daily["Date"] = pd.to_datetime(daily["Date"], format="%d-%b-%Y")
            daily = daily.sort_values("Date")

            # Construct OHLC (Synthetic: Open=Close, High=Close, Low=Close)
            # This is not ideal but better than random for testing pipeline
            # Better: add some noise

            result = pd.DataFrame()
            result["date"] = daily["Date"]
            close = daily["Underlying Value"]

            # Add synthetic variation
            np.random.seed(42)
            volatility = 0.01

            result["open"] = close * (1 + np.random.normal(0, volatility/2, len(close)))
            result["high"] = np.maximum(result["open"], close * (1 + abs(np.random.normal(0, volatility, len(close)))))
            result["low"] = np.minimum(result["open"], close * (1 - abs(np.random.normal(0, volatility, len(close)))))
            result["close"] = close
            result["adj_close"] = close
            result["volume"] = 1000000 # Dummy volume

            return result
        except Exception as e:
            logger.error("Failed to extract seed data", error=str(e))
            return None

    def _generate_synthetic(self, symbol: str) -> pd.DataFrame:
        """Generate synthetic random walk data"""
        logger.warning("Generating synthetic data", symbol=symbol)
        dates = pd.date_range(end=datetime.now(), periods=365*2, freq="B")
        n = len(dates)

        start_price = 24000 if symbol == "NIFTY" else 75000
        returns = np.random.normal(0.0005, 0.01, n)
        price = start_price * np.exp(np.cumsum(returns))

        df = pd.DataFrame({
            "date": dates,
            "close": price,
            "adj_close": price
        })

        # Synthetic OHLC
        df["open"] = df["close"].shift(1).fillna(start_price) * (1 + np.random.normal(0, 0.002, n))
        df["high"] = np.maximum(df["open"], df["close"]) * (1 + abs(np.random.normal(0, 0.005, n)))
        df["low"] = np.minimum(df["open"], df["close"]) * (1 - abs(np.random.normal(0, 0.005, n)))
        df["volume"] = np.random.randint(100000, 1000000, n)

        return df

    def load_data(self, symbol: str, force_refresh: bool = False) -> pd.DataFrame:
        cache_path = self._get_cache_path(symbol)
        df = None

        # 1. Try Cache
        if not force_refresh and os.path.exists(cache_path):
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
                if (datetime.now() - mtime).days < 1:
                    logger.info("Using cached data", symbol=symbol)
                    df = pd.read_csv(cache_path)
                else:
                    logger.info("Cache stale", symbol=symbol)
            except Exception:
                pass

        # 2. Try Download
        if df is None:
            raw_df = self.download_data(symbol)
            if raw_df is not None:
                df = raw_df
                df.to_csv(cache_path, index=False)

        # 3. Fallback to Stale Cache
        if df is None and os.path.exists(cache_path):
             logger.warning("Using stale cache", symbol=symbol)
             df = pd.read_csv(cache_path)

        # 4. Fallback to Seed Data (NIFTY from options)
        if df is None and symbol == "NIFTY":
            df = self._extract_from_seed(symbol)
            if df is not None:
                df.to_csv(cache_path, index=False)

        # 5. Fallback to Synthetic
        if df is None:
            df = self._generate_synthetic(symbol)
            df.to_csv(cache_path, index=False)

        # Normalize
        df.columns = [c.lower().replace(" ", "") for c in df.columns]

        rename_map = {
            "date": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "adjclose": "adj_close",
            "volume": "volume"
        }
        df = df.rename(columns=rename_map)

        # Ensure date format
        if not pd.api.types.is_datetime64_any_dtype(df["date"]):
            df["date"] = pd.to_datetime(df["date"])

        df = df.sort_values("date")
        df = df.set_index("date")

        # Validation
        df = df.ffill().dropna()

        return df

if __name__ == "__main__":
    loader = DataLoader()
    try:
        df = loader.load_data("NIFTY")
        print(df.tail())
    except Exception as e:
        print(e)
