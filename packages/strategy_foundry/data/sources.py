import requests
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO
import logging
import time
import random

logger = logging.getLogger(__name__)

YAHOO_URL = "https://query1.finance.yahoo.com/v7/finance/download/{symbol}?period1={start}&period2={end}&interval={interval}&events=history&includeAdjustedClose=true"

class YahooSource:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
        ]

    def download(self, symbol: str, interval: str = "1d", days: int = 365) -> pd.DataFrame:
        """
        Download OHLCV data from Yahoo Finance.

        Args:
            symbol: Ticker symbol (e.g. ^NSEI)
            interval: 1d, 5m, 15m
            days: Number of days of history to fetch
        """
        # Add 1 day buffer to end_dt to ensure we get today's data if available
        end_dt = datetime.now() + timedelta(days=1)
        start_dt = end_dt - timedelta(days=days + 5) # Buffer

        # Yahoo expects unix timestamp
        period1 = int(start_dt.timestamp())
        period2 = int(end_dt.timestamp())

        url = YAHOO_URL.format(symbol=symbol, start=period1, end=period2, interval=interval)

        logger.info(f"Downloading {symbol} ({interval}) from Yahoo...")

        headers = {
            "User-Agent": random.choice(self.user_agents)
        }

        try:
            response = requests.get(url, headers=headers, timeout=15.0)

            if response.status_code == 404:
                logger.warning(f"Symbol {symbol} not found on Yahoo.")
                return None

            if response.status_code == 429:
                logger.warning(f"Rate limited by Yahoo. Sleeping 5s.")
                time.sleep(5)
                return None

            response.raise_for_status()

            if not response.text:
                logger.warning(f"Empty response for {symbol}")
                return None

            try:
                df = pd.read_csv(StringIO(response.text))
            except pd.errors.ParserError:
                 logger.warning(f"Failed to parse CSV for {symbol}")
                 return None

            # Standardize columns
            df.columns = [c.lower() for c in df.columns]
            if 'date' in df.columns:
                df.rename(columns={'date': 'datetime'}, inplace=True)

            # Parse datetime
            # Yahoo intraday is usually UTC. Daily is local date string.
            if interval in ['5m', '15m']:
                df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
            else:
                # Daily is usually YYYY-MM-DD
                df['datetime'] = pd.to_datetime(df['datetime'])
                # Localize to UTC then to IST? Or just assume it's exchange local time?
                # Yahoo daily date is usually exchange local date.
                # Let's keep it naive or assume IST for consistency later.
                # Actually Loader handles timezone conversion.
                # But we need to know what it is.
                # For daily, let's assume it's the date of the session.

            df.dropna(inplace=True)

            # Ensure float columns
            cols = ['open', 'high', 'low', 'close', 'adj close', 'volume']
            for c in cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce')

            df.dropna(inplace=True)

            if df.empty:
                return None

            return df

        except Exception as e:
            logger.error(f"Failed to download {symbol}: {e}")
            return None
