"""Data source interfaces and implementations"""
import abc
import datetime
import json
import time
from typing import Dict, List, Optional
import requests
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

class DataSource(abc.ABC):
    @abc.abstractmethod
    def fetch_ohlcv(self, symbol: str, interval: str, range_: str = "max") -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data.

        Args:
            symbol: Ticker symbol
            interval: Bar interval (e.g. 1d, 5m, 15m)
            range_: Data range (e.g. 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

        Returns:
            DataFrame with index 'timestamp' (datetime, UTC or localized) and columns:
            open, high, low, close, volume (all float).
            Returns None if fetch fails.
        """
        pass

class YahooSource(DataSource):
    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }

    def fetch_ohlcv(self, symbol: str, interval: str, range_: str = "max") -> Optional[pd.DataFrame]:
        url = self.BASE_URL.format(symbol=symbol)
        params = {
            "interval": interval,
            "range": range_,
            "includePrePost": "false" # Intraday usually doesn't have pre/post for indices often, but good to be explicit
        }

        try:
            logger.info("Fetching data from Yahoo", symbol=symbol, interval=interval, range=range_)
            response = requests.get(url, params=params, headers=self.HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()

            return self._parse_yahoo_response(data)
        except Exception as e:
            logger.error("Yahoo fetch failed", symbol=symbol, error=str(e))
            return None

    def _parse_yahoo_response(self, data: Dict) -> Optional[pd.DataFrame]:
        try:
            result = data["chart"]["result"][0]
            meta = result["meta"]
            timestamps = result["timestamp"]
            indicators = result["indicators"]["quote"][0]

            df = pd.DataFrame({
                "timestamp": pd.to_datetime(timestamps, unit="s", utc=True),
                "open": indicators["open"],
                "high": indicators["high"],
                "low": indicators["low"],
                "close": indicators["close"],
                "volume": indicators.get("volume", [0]*len(timestamps))
            })

            # Filter out NaNs (often happens if no trades in that minute)
            df.dropna(subset=["open", "high", "low", "close"], inplace=True)

            df.set_index("timestamp", inplace=True)
            return df
        except (KeyError, IndexError, TypeError) as e:
            logger.warning("Error parsing Yahoo response", error=str(e))
            return None
