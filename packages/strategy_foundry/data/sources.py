import requests
import pandas as pd
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

class YahooSource:
    """Yahoo Finance data source using direct API calls"""

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def fetch_ohlcv(self, symbol: str, interval: str, period: str = "max") -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data from Yahoo Finance.

        Args:
            symbol: Yahoo Finance symbol (e.g., ^NSEI)
            interval: 5m, 15m, 1d
            period: 60d, 1y, 10y, max

        Returns:
            DataFrame with Index=Date, Open, High, Low, Close, Volume
        """
        url = self.BASE_URL.format(symbol=symbol)
        params = {
            "interval": interval,
            "range": period,
            "events": "div,splits"
        }

        try:
            logger.info("Fetching data from Yahoo", symbol=symbol, interval=interval, period=period)
            response = requests.get(url, headers=self.HEADERS, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            result = data["chart"]["result"][0]
            timestamps = result["timestamp"]
            quote = result["indicators"]["quote"][0]

            df = pd.DataFrame({
                "Date": pd.to_datetime(timestamps, unit="s", utc=True).tz_convert("Asia/Kolkata"),
                "Open": quote["open"],
                "High": quote["high"],
                "Low": quote["low"],
                "Close": quote["close"],
                "Volume": quote["volume"]
            })

            df = df.dropna()
            df = df.set_index("Date")
            df = df.sort_index()

            return df

        except Exception as e:
            logger.error("Failed to fetch data from Yahoo", symbol=symbol, error=str(e))
            return None
