import os
import requests
import pandas as pd
import yaml
import structlog
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

logger = structlog.get_logger(__name__)

def load_config():
    config_path = Path("packages/strategy_foundry/configs/foundry.yaml")
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return {}

def load_instrument_map():
    map_path = Path("packages/strategy_foundry/configs/instrument_map.yaml")
    if map_path.exists():
        with open(map_path, "r") as f:
            return yaml.safe_load(f)
    return {}

class DataLoader:
    def __init__(self, cache_dir: str = "packages/strategy_foundry/data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.config = load_config()
        self.instrument_map = load_instrument_map()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        })

    def get_symbol_ticker(self, instrument: str) -> str:
        return self.instrument_map.get("research", {}).get(instrument, instrument)

    def get_proxy_ticker(self, instrument: str) -> str:
        return self.instrument_map.get("paper_proxy", {}).get(instrument, None)

    def fetch_yahoo(self, ticker: str, interval: str, range_str: str) -> pd.DataFrame:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        params = {
            "interval": interval,
            "range": range_str,
            "includePrePost": "false"
        }
        try:
            resp = self.session.get(url, params=params, timeout=10)
            if resp.status_code == 404:
                logger.warning(f"Ticker {ticker} not found")
                return pd.DataFrame()
            if resp.status_code == 429:
                logger.warning(f"Rate limited for {ticker}")
                return pd.DataFrame()

            resp.raise_for_status()
            data = resp.json()

            if "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
                logger.error("No data in response", ticker=ticker)
                return pd.DataFrame()

            result = data["chart"]["result"][0]
            if "timestamp" not in result:
                 return pd.DataFrame()

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

            # Drop rows with NaN OHLC (sometimes happens)
            df.dropna(subset=["open", "high", "low", "close"], inplace=True)

            # Fill volume NaN with 0
            df["volume"] = df["volume"].fillna(0)

            return df
        except Exception as e:
            logger.error("Failed to fetch yahoo data", ticker=ticker, error=str(e))
            return pd.DataFrame()

    def get_data(self, instrument: str, timeframe: str, force_refresh: bool = False) -> pd.DataFrame:
        ticker = self.get_symbol_ticker(instrument)
        y_interval = timeframe

        # Map foundry timeframe to yahoo
        if timeframe == "1d":
            y_range = "5y" # 5y is safer than 10y for payload size
        elif timeframe in ["5m", "15m"]:
            y_range = "60d" # Yahoo max for intraday
        else:
            y_range = "60d"

        cache_file = self.cache_dir / f"{instrument}_{timeframe}.csv"

        # Check cache validity
        is_cache_valid = False
        if cache_file.exists():
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            # Valid if less than 60 mins old (since we run hourly)
            if datetime.now() - mtime < timedelta(minutes=60):
                is_cache_valid = True

        if not force_refresh and is_cache_valid:
            try:
                df = pd.read_csv(cache_file)
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                return df
            except Exception:
                logger.warning("Corrupt cache, refetching")

        # Fetch
        df = self.fetch_yahoo(ticker, y_interval, y_range)

        if df.empty:
            # Fallback
            proxy = self.get_proxy_ticker(instrument)
            if proxy and proxy != ticker:
                logger.info(f"Fallback to proxy {proxy} for {instrument}")
                df = self.fetch_yahoo(proxy, y_interval, y_range)

        if not df.empty:
            df.to_csv(cache_file, index=False)

        return df
