"""
Lightweight Yahoo Finance data source using requests.
No heavy dependencies like yfinance.
"""
import csv
import io
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import requests
import structlog
import pandas as pd

logger = structlog.get_logger(__name__)

class YahooSource:
    """
    Fetches historical OHLCV data from Yahoo Finance.
    """
    BASE_URL = "https://query1.finance.yahoo.com/v7/finance/download/{symbol}"

    # Headers to mimic a browser and avoid 429s
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Accept": "text/csv,application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://finance.yahoo.com",
        "Referer": "https://finance.yahoo.com/"
    }

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update(self.HEADERS)

    def download_csv(self, symbol: str, interval: str, days: int) -> Optional[pd.DataFrame]:
        """
        Download CSV data from Yahoo Finance.

        Args:
            symbol: Yahoo finance symbol (e.g. ^NSEI)
            interval: Timeframe (1d, 5m, 15m)
            days: Number of days of history to fetch

        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Adj Close, Volume
        """
        try:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=days)

            period1 = int(start_dt.timestamp())
            period2 = int(end_dt.timestamp())

            params = {
                "period1": period1,
                "period2": period2,
                "interval": interval,
                "events": "history",
                "includeAdjustedClose": "true"
            }

            url = self.BASE_URL.format(symbol=symbol)
            logger.info("Fetching data", symbol=symbol, interval=interval, days=days)

            # Simple retry logic
            for attempt in range(3):
                try:
                    # First, visit the quote page to get cookies/crumbs (essential for Yahoo)
                    # This is a lightweight "crumb" fetch simulation by just hitting the main page
                    if attempt == 0:
                        self.session.get("https://finance.yahoo.com/quote/{}".format(symbol), timeout=10)

                    response = self.session.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    break
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        logger.warning("Rate limit hit, sleeping...", attempt=attempt)
                        time.sleep(2 * (attempt + 1))
                    elif e.response.status_code == 404:
                         logger.error("Symbol not found", symbol=symbol)
                         return None
                    else:
                        raise e
                except Exception as e:
                    logger.warning("Fetch attempt failed", error=str(e), attempt=attempt)
                    if attempt == 2:
                        return None
                    time.sleep(1)

            # Parse CSV
            content = response.content.decode('utf-8')
            if "Date,Open,High,Low,Close" not in content:
                logger.error("Invalid CSV content received", symbol=symbol)
                return None

            df = pd.read_csv(io.StringIO(content))

            # Clean and normalize
            # Rename Date -> timestamp or datetime index?
            # Keeping as standard columns first
            if "Date" in df.columns:
                # Yahoo intraday dates are "Datetime" usually, daily is "Date"
                # But read_csv might handle header automatically
                pass
            elif "Datetime" in df.columns:
                df.rename(columns={"Datetime": "Date"}, inplace=True)

            df["Date"] = pd.to_datetime(df["Date"], utc=True)

            # Convert to IST
            df["Date"] = df["Date"].dt.tz_convert("Asia/Kolkata")

            # Remove timezone info to make it naive (but in IST time) or keep aware?
            # The prompt asks for "Normalize reporting timestamps to Asia/Kolkata".
            # Core uses naive datetime in some places, but let's stick to tz-aware where possible
            # or naive if that's what core expects.
            # Core HistoricalDataLoader returns pydatetime which usually naive in this repo context
            # Let's make it naive IST for compatibility with simple backtesters
            df["Date"] = df["Date"].dt.tz_localize(None)

            df.set_index("Date", inplace=True)
            df.sort_index(inplace=True)

            # Drop Adj Close if not needed, or keep it
            if "Adj Close" in df.columns:
                df.drop(columns=["Adj Close"], inplace=True)

            # Filter NaNs
            df.dropna(inplace=True)

            return df

        except Exception as e:
            logger.error("Yahoo download failed", symbol=symbol, error=str(e))
            return None
