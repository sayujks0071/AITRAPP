import os
import datetime
import pandas as pd
import requests
import structlog
from pathlib import Path
from io import StringIO

logger = structlog.get_logger(__name__)

CACHE_DIR = Path("packages/strategy_foundry/data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Symbol mapping
SYMBOL_MAP = {
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN"
}

class DataLoader:
    """Loads daily OHLCV data for indices."""

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir

    def load_data(self, symbol: str, force_download: bool = False) -> pd.DataFrame:
        """
        Load data for a symbol (NIFTY or SENSEX).
        Checks cache validity. If last data point is older than yesterday, attempts refresh.
        """
        if symbol not in SYMBOL_MAP:
            raise ValueError(f"Unknown symbol: {symbol}")

        y_symbol = SYMBOL_MAP[symbol]
        cache_file = self.cache_dir / f"{symbol}.csv"

        df = None
        needs_update = force_download

        if cache_file.exists():
            try:
                df = pd.read_csv(cache_file, parse_dates=["date"], index_col="date")
                if df.index.tz is None:
                     df.index = df.index.tz_localize("UTC").tz_convert("Asia/Kolkata")
                else:
                     df.index = df.index.tz_convert("Asia/Kolkata")

                # Check freshness
                if not needs_update and not df.empty:
                    last_date = df.index[-1].date()
                    today = datetime.datetime.now().date()

                    # If data is not from today or yesterday, and it's a weekday, we might need update.
                    # Simple check: If last date < Today - 1 day, it's stale.
                    # (Allowing yesterday's close to remain valid until tonight's update)
                    if last_date < (today - datetime.timedelta(days=1)):
                        # But wait, if yesterday was Sunday, last date would be Friday.
                        # Logic: if last_date < (Today - 3 days) -> definitely stale.
                        # Better: attempt update if explicitly stale or just "run update hourly".
                        # The runner will likely rely on this method to decide.
                        # Let's be aggressive: update if last date is not today.
                        # Yahoo updates daily.
                        needs_update = True
                        logger.info("Cache stale", symbol=symbol, last_date=last_date)

            except Exception as e:
                logger.warning("Failed to load cache, will download", error=str(e))
                needs_update = True

        if needs_update or df is None:
            try:
                df = self.download_data(symbol, y_symbol, cache_file)
            except Exception as e:
                logger.error("Download failed, using cache if available", error=str(e))
                if df is None:
                    raise

        return df

    def download_data(self, symbol: str, y_symbol: str, cache_file: Path) -> pd.DataFrame:
        """Download data from Yahoo Finance using requests."""
        logger.info("Downloading data", symbol=symbol, y_symbol=y_symbol)

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{y_symbol}"
        params = {
            "interval": "1d",
            "range": "10y"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }

        resp = requests.get(url, params=params, headers=headers, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()

        try:
            result = data["chart"]["result"][0]
            timestamps = result["timestamp"]
            quote = result["indicators"]["quote"][0]

            df = pd.DataFrame({
                "timestamp": pd.to_datetime(timestamps, unit="s"),
                "open": quote["open"],
                "high": quote["high"],
                "low": quote["low"],
                "close": quote["close"],
                "volume": quote["volume"]
            })

            # Filter incomplete rows
            df = df.dropna()

            # Set index to datetime
            df.set_index("timestamp", inplace=True)

            # Localize to IST
            df.index = df.index.tz_localize("UTC").tz_convert("Asia/Kolkata")
            df.index.name = "date"

            # Validate Columns
            for col in ["open", "high", "low", "close"]:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            df = df[df["high"] >= df["low"]]

            # Save to CSV
            df.to_csv(cache_file)
            logger.info("Downloaded and cached data", symbol=symbol, rows=len(df))

            return df

        except Exception as e:
            logger.error("Failed to parse Yahoo data", error=str(e))
            raise
