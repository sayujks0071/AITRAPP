import requests
import pandas as pd
import io
from datetime import datetime, timedelta
import time
import structlog

logger = structlog.get_logger(__name__)

class YahooSource:
    """
    Lightweight Yahoo Finance downloader using requests.
    """
    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def fetch_ohlcv(self, symbol: str, interval: str, range_str: str = "1mo") -> pd.DataFrame:
        """
        Fetch OHLCV data from Yahoo Finance.

        Args:
            symbol: Ticker symbol (e.g., ^NSEI)
            interval: Bar interval (e.g., 5m, 15m, 1d)
            range_str: Range string (e.g., 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

        Returns:
            DataFrame with Open, High, Low, Close, Volume, index as DatetimeIndex (Asia/Kolkata)
        """
        params = {
            "interval": interval,
            "range": range_str,
            "includePrePost": "false",
            "events": "div,split"
        }

        url = self.BASE_URL.format(symbol=symbol)

        try:
            logger.info(f"Fetching {symbol} {interval} from Yahoo...", url=url)
            response = requests.get(url, headers=self.HEADERS, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            return self._parse_yahoo_json(data)

        except Exception as e:
            logger.error(f"Yahoo fetch failed for {symbol}", error=str(e))
            return pd.DataFrame()

    def _parse_yahoo_json(self, data: dict) -> pd.DataFrame:
        try:
            result = data["chart"]["result"][0]
            timestamps = result["timestamp"]
            indicators = result["indicators"]["quote"][0]

            df = pd.DataFrame({
                "timestamp": pd.to_datetime(timestamps, unit="s", utc=True),
                "open": indicators["open"],
                "high": indicators["high"],
                "low": indicators["low"],
                "close": indicators["close"],
                "volume": indicators["volume"]
            })

            # Drop NaNs (sometimes Yahoo returns nulls for failed ticks)
            df.dropna(inplace=True)

            # Convert to Asia/Kolkata
            df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
            df.set_index("timestamp", inplace=True)

            return df

        except KeyError as e:
            logger.error("Malformed Yahoo response", error=str(e))
            return pd.DataFrame()
        except Exception as e:
            logger.error("Error parsing Yahoo data", error=str(e))
            return pd.DataFrame()

class DataSourceRegistry:
    def __init__(self):
        self.yahoo = YahooSource()

    def get_yahoo(self):
        return self.yahoo
