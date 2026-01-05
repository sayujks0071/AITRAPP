"""
Data Sources
Handles downloading data from external sources (Yahoo Finance) with caching.
"""
import requests
import pandas as pd
import io
import structlog
from datetime import datetime, timedelta
import time
import os
import random

logger = structlog.get_logger(__name__)

class YahooDownloader:
    """Lightweight Yahoo Finance downloader using requests"""

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    ]

    @staticmethod
    def download(symbol: str, interval: str = "1d", range_str: str = "1y") -> pd.DataFrame:
        """
        Download OHLCV data from Yahoo Finance.

        Args:
            symbol: Ticker symbol (e.g. ^NSEI)
            interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
            range_str: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

        Returns:
            DataFrame with Open, High, Low, Close, Volume and Datetime index (UTC)
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "range": range_str,
            "events": "div,splits"
        }

        headers = {
            "User-Agent": random.choice(YahooDownloader.USER_AGENTS)
        }

        url = YahooDownloader.BASE_URL.format(symbol=symbol)

        try:
            logger.info(f"Downloading {symbol} interval={interval} range={range_str}")
            # Add a small delay/jitter to be polite
            time.sleep(random.uniform(0.5, 1.5))

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            if "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
                logger.error(f"No data found for {symbol}")
                return pd.DataFrame()

            result = data["chart"]["result"][0]

            if "timestamp" not in result:
                return pd.DataFrame()

            timestamps = result["timestamp"]
            quote = result["indicators"]["quote"][0]

            df = pd.DataFrame({
                "timestamp": pd.to_datetime(timestamps, unit="s"),
                "open": quote.get("open", []),
                "high": quote.get("high", []),
                "low": quote.get("low", []),
                "close": quote.get("close", []),
                "volume": quote.get("volume", [])
            })

            # Filter incomplete rows
            df = df.dropna()

            # Set index
            df.set_index("timestamp", inplace=True)

            return df

        except Exception as e:
            logger.error(f"Download failed for {symbol}: {str(e)}")
            return pd.DataFrame()

class DataSources:
    @staticmethod
    def get_yahoo_data(symbol: str, interval: str, period: str = "60d") -> pd.DataFrame:
        # Convert foundry intervals to Yahoo intervals
        yahoo_interval = interval
        if interval == "15m":
            yahoo_interval = "15m"
        elif interval == "5m":
            yahoo_interval = "5m"
        elif interval == "1d":
            yahoo_interval = "1d"
            period = "2y" # Longer for daily

        # Adjust period for intraday
        # Yahoo limits: 1m (7d), 5m (60d), 15m (60d)
        if interval in ["5m", "15m"] and period == "max":
            period = "60d"

        return YahooDownloader.download(symbol, yahoo_interval, period)
