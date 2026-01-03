import datetime
import requests
import pandas as pd
import structlog
import time
from typing import Optional

logger = structlog.get_logger(__name__)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

def download_yahoo_ohlcv(symbol: str, interval: str = "1d", period: str = "max") -> Optional[pd.DataFrame]:
    """
    Download OHLCV data from Yahoo Finance via non-official API.

    Args:
        symbol: Yahoo symbol (e.g., ^NSEI)
        interval: 1d, 5m, 15m
        period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

    Returns:
        DataFrame with Open, High, Low, Close, Volume, datetime index localized to Asia/Kolkata
    """
    # Map interval to Yahoo format if needed (they match mostly)
    # Valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    params = {
        "interval": interval,
        "range": period,
        "includePrePost": "false",
        "events": "div,split"
    }

    headers = {
        "User-Agent": USER_AGENT
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
            logger.error("No data found for symbol", symbol=symbol)
            return None

        result = data["chart"]["result"][0]
        meta = result["meta"]
        indicators = result["indicators"]["quote"][0]
        timestamps = result["timestamp"]

        df = pd.DataFrame({
            "timestamp": pd.to_datetime(timestamps, unit="s"),
            "open": indicators["open"],
            "high": indicators["high"],
            "low": indicators["low"],
            "close": indicators["close"],
            "volume": indicators["volume"]
        })

        # Localize
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata")
        df.set_index("timestamp", inplace=True)

        # Drop NaNs
        df.dropna(inplace=True)

        return df

    except Exception as e:
        logger.error("Failed to download data", symbol=symbol, error=str(e))
        return None
