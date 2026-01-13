"""Data sources for Strategy Foundry"""
import requests
import pandas as pd
import structlog
from datetime import datetime
import time

logger = structlog.get_logger(__name__)

class YahooSource:
    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }

    def fetch_ohlcv(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Fetch OHLCV data from Yahoo Finance.

        Args:
            symbol: Yahoo symbol (e.g., ^NSEI)
            timeframe: '5m', '15m', '1d'

        Returns:
            DataFrame with Index=Date, Open, High, Low, Close, Volume
        """
        # Map timeframe to Yahoo interval/range
        interval = timeframe
        if timeframe == "1D":
            interval = "1d"
            range_str = "5y" # Long history for daily
        elif timeframe in ["5m", "15m"]:
            # Yahoo limit for intraday is usually 60d
            range_str = "59d"
        else:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        params = {
            "interval": interval,
            "range": range_str,
            "includePrePost": "false"
        }

        url = self.BASE_URL.format(symbol=symbol)

        try:
            logger.info("Fetching data from Yahoo", symbol=symbol, interval=interval)
            response = requests.get(url, params=params, headers=self.HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()

            result = data["chart"]["result"][0]
            meta = result["meta"]
            timestamps = result["timestamp"]
            indicators = result["indicators"]["quote"][0]

            df = pd.DataFrame({
                "timestamp": pd.to_datetime(timestamps, unit="s", utc=True).tz_convert("Asia/Kolkata"),
                "open": indicators["open"],
                "high": indicators["high"],
                "low": indicators["low"],
                "close": indicators["close"],
                "volume": indicators["volume"]
            })

            # Drop NaNs
            df.dropna(inplace=True)

            # Set index
            df.set_index("timestamp", inplace=True)

            return df

        except Exception as e:
            logger.error("Yahoo fetch failed", symbol=symbol, error=str(e))
            return pd.DataFrame()
