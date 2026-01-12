import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import structlog
import yaml
import time
from typing import Optional
import pytz

logger = structlog.get_logger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CONFIG_DIR = Path(__file__).parent.parent / "configs"
IST = pytz.timezone("Asia/Kolkata")

class DataLoader:
    def __init__(self):
        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.proxies = self._load_proxies()

    def _load_proxies(self):
        try:
            with open(CONFIG_DIR / "instrument_map.yaml") as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    def get_symbol_map(self, symbol: str) -> str:
        # Default to research mapping
        if self.proxies and "research" in self.proxies:
            return self.proxies["research"].get(symbol, symbol)
        return symbol

    def get_fallback_symbol(self, symbol: str) -> Optional[str]:
        if self.proxies and "research_fallback" in self.proxies:
            return self.proxies["research_fallback"].get(symbol)
        return None

    def fetch_data(self, symbol: str, timeframe: str, lookback_days: int = 60) -> pd.DataFrame:
        """
        Fetch data for symbol.
        symbol: e.g. "NIFTY" (will be mapped to ^NSEI)
        timeframe: "5m", "15m", "1D"
        """
        mapped_symbol = self.get_symbol_map(symbol)
        cache_file = self.cache_dir / f"{symbol}_{timeframe}.csv"

        if cache_file.exists():
            # Basic cache validation
            try:
                df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                if not df.empty:
                    last_date = df.index[-1]
                    # If data is recent enough (e.g. from today or yesterday), use it?
                    # For intraday, we ideally want up to the minute.
                    if datetime.now(IST) - last_date < timedelta(minutes=15) and timeframe != "1D":
                         return df
            except Exception:
                pass

        # Fetch fresh
        logger.info("Fetching fresh data", symbol=mapped_symbol, timeframe=timeframe)
        try:
            df = self._download_yahoo_chart(mapped_symbol, timeframe, lookback_days)

            if df is not None and not df.empty:
                df.to_csv(cache_file)
                return df
        except Exception as e:
            logger.error("Fetch failed", error=str(e))
            # Try Fallback
            fallback = self.get_fallback_symbol(symbol)
            if fallback:
                logger.info("Retrying with fallback", symbol=fallback)
                try:
                    df = self._download_yahoo_chart(fallback, timeframe, lookback_days)
                    if df is not None and not df.empty:
                        df.to_csv(cache_file)
                        return df
                except Exception as e2:
                    logger.error("Fallback fetch failed", error=str(e2))

        # Fallback to cache if download failed
        if cache_file.exists():
             logger.warning("Download failed, using stale cache", symbol=symbol)
             return pd.read_csv(cache_file, index_col=0, parse_dates=True)

        raise ValueError(f"No data available for {symbol}")

    def _download_yahoo_chart(self, symbol: str, timeframe: str, days: int) -> Optional[pd.DataFrame]:
        # Use v8/finance/chart API for intraday support
        # intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        interval = timeframe.lower()
        if interval == "1d": interval = "1d"

        # Use range instead of period1/period2 for simpler intraday queries often
        # But for specific history, period1/period2 is better.
        end_ts = int(time.time())
        start_ts = int((datetime.now() - timedelta(days=days)).timestamp())

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            "period1": start_ts,
            "period2": end_ts,
            "interval": interval,
            "includePrePost": "false",
            "events": "div,splits"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }

        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()

        data = resp.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return None

        quote = result[0]
        meta = quote.get("meta", {})
        indicators = quote.get("indicators", {}).get("quote", [{}])[0]
        timestamps = quote.get("timestamp", [])

        if not timestamps:
            return None

        df = pd.DataFrame({
            "open": indicators.get("open", []),
            "high": indicators.get("high", []),
            "low": indicators.get("low", []),
            "close": indicators.get("close", []),
            "volume": indicators.get("volume", [])
        }, index=pd.to_datetime(timestamps, unit="s"))

        # Drop missing
        df = df.dropna()
        df.index.name = "Date"

        # Handle Timezone
        # Yahoo chart response includes meta.gmtoffset or timezone info?
        # Usually timestamps are UTC unix.
        # We need to localize to IST.
        # If we just localize UTC -> IST, check if that matches market hours.
        # 9:15 IST is 3:45 UTC.

        # Localize to UTC then convert
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")

        df.index = df.index.tz_convert(IST)

        return df[["open", "high", "low", "close", "volume"]]
