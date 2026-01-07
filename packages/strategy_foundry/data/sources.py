"""
Data Sources
Manages fetching data from external sources (Yahoo Finance via requests)
"""
import requests
import pandas as pd
import io
import structlog
from datetime import datetime, timedelta
import time
from typing import Optional

logger = structlog.get_logger(__name__)

class DataSources:
    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    @staticmethod
    def get_yahoo_data(symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Fetch OHLCV data from Yahoo Finance.

        Args:
            symbol: Yahoo Finance symbol (e.g., ^NSEI)
            timeframe: "5m", "15m", "1d"

        Returns:
            pd.DataFrame with index as Datetime (UTC), columns: Open, High, Low, Close, Volume
        """

        # Map timeframe to Yahoo interval and range
        interval_map = {
            "5m": "5m",
            "15m": "15m",
            "1d": "1d"
        }

        range_map = {
            "5m": "60d",   # Max for 5m is ~60d via API usually
            "15m": "60d",  # Max for 15m
            "1d": "5y"     # 5 years for daily
        }

        if timeframe not in interval_map:
            logger.error(f"Unsupported timeframe: {timeframe}")
            return pd.DataFrame()

        interval = interval_map[timeframe]
        range_ = range_map[timeframe]

        params = {
            "symbol": symbol,
            "interval": interval,
            "range": range_,
            "includePrePost": "false",
            "events": "div|split"
        }

        # Browser-like headers to avoid 429
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }

        url = DataSources.BASE_URL.format(symbol=symbol)

        try:
            logger.info(f"Requesting {url} with params {params}")
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            if "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
                logger.error(f"No data found in response for {symbol}")
                return pd.DataFrame()

            result = data["chart"]["result"][0]

            if "timestamp" not in result or "indicators" not in result:
                logger.error(f"Missing timestamp or indicators for {symbol}")
                return pd.DataFrame()

            timestamps = result["timestamp"]
            quote = result["indicators"]["quote"][0]

            df = pd.DataFrame({
                "timestamp": timestamps,
                "Open": quote.get("open", []),
                "High": quote.get("high", []),
                "Low": quote.get("low", []),
                "Close": quote.get("close", []),
                "Volume": quote.get("volume", [])
            })

            # Drop rows with NaN (missing data)
            df.dropna(inplace=True)

            # Convert timestamp to datetime (UTC) then to IST
            from packages.strategy_foundry.adapters.core_market_hours import IST
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_convert(IST)
            df.set_index("timestamp", inplace=True)
            df.sort_index(inplace=True)

            return df

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching {symbol}: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error parsing data for {symbol}: {e}")
            return pd.DataFrame()
