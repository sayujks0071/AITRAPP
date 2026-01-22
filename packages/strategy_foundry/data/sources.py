import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

class YahooSource:
    """
    Fetches OHLCV data from Yahoo Finance (unofficial API).
    """

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"

    @staticmethod
    def fetch(symbol: str, interval: str, range_str: str = "max") -> Optional[pd.DataFrame]:
        """
        Fetch data from Yahoo Finance.

        Args:
            symbol: Ticker symbol (e.g. ^NSEI)
            interval: 5m, 15m, 1d
            range_str: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, max

        Returns:
            DataFrame with datetime index (Asia/Kolkata) and columns: open, high, low, close, volume.
        """
        url = YahooSource.BASE_URL.format(symbol=symbol)
        params = {
            "interval": interval,
            "range": range_str,
            "includePrePost": "false"
        }
        headers = {
            "User-Agent": YahooSource.USER_AGENT
        }

        max_retries = 3
        backoff = 2

        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching {symbol} {interval} from Yahoo (attempt {attempt+1})...")
                response = requests.get(url, params=params, headers=headers, timeout=10)

                if response.status_code == 429:
                    logger.warning(f"Rate limited (429). Sleeping {backoff}s...")
                    time.sleep(backoff)
                    backoff *= 2
                    continue

                response.raise_for_status()
                data = response.json()

                chart = data.get("chart", {}).get("result", [None])[0]
                if not chart:
                    logger.error(f"No data found for {symbol}")
                    return None

                timestamp = chart.get("timestamp", [])
                indicators = chart.get("indicators", {}).get("quote", [None])[0]

                if not timestamp or not indicators:
                    logger.error(f"Empty payload for {symbol}")
                    return None

                df = pd.DataFrame({
                    "timestamp": pd.to_datetime(timestamp, unit="s", utc=True),
                    "open": indicators.get("open", []),
                    "high": indicators.get("high", []),
                    "low": indicators.get("low", []),
                    "close": indicators.get("close", []),
                    "volume": indicators.get("volume", [])
                })

                # Convert timezone
                df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
                df.set_index("timestamp", inplace=True)

                # Drop NaNs
                df.dropna(inplace=True)

                # Sort
                df.sort_index(inplace=True)

                logger.info(f"Fetched {len(df)} rows for {symbol}")
                return df

            except Exception as e:
                logger.error(f"Failed to fetch {symbol}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2

        return None
