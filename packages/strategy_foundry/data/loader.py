"""
Data Loader
Handles fetching and caching of OHLCV data.
Priority: Core Provider > Yahoo Fallback
"""
import pandas as pd
import requests
import os
import yaml
from datetime import datetime, timedelta
from io import StringIO
import structlog
from packages.strategy_foundry.adapters.core_market_hours import MarketHours

logger = structlog.get_logger(__name__)

class DataLoader:
    def __init__(self, config_path="packages/strategy_foundry/configs/foundry.yaml", instrument_map_path="packages/strategy_foundry/configs/instrument_map.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        with open(instrument_map_path) as f:
            self.instrument_map = yaml.safe_load(f)

        self.cache_dir = self.config['system']['cache_dir']
        self.research_map = self.instrument_map.get('research', {})
        self.proxies = self.instrument_map.get('paper_proxy', {})

    def get_data(self, instrument: str, timeframe: str, days: int = None) -> pd.DataFrame:
        """
        Get OHLCV data for instrument and timeframe.
        """
        # Determine symbol
        symbol = self.research_map.get(instrument, instrument)

        # Determine duration
        if days is None:
            if timeframe == "1D":
                days = self.config['data']['daily']['max_days']
            else:
                days = self.config['data']['intraday']['max_days']

        # Try cache first (if recent enough)
        # TODO: Implement strict cache validity check. For now, we overwrite if we fetch.

        # Fetch fresh
        try:
            df = self._fetch_yahoo(symbol, timeframe, days)
            self._save_cache(instrument, timeframe, df)
            return df
        except Exception as e:
            logger.error(f"Failed to fetch data for {instrument} {timeframe}", error=str(e))
            # Try loading cache as fallback
            return self._load_cache(instrument, timeframe)

    def _fetch_yahoo(self, symbol: str, timeframe: str, days: int) -> pd.DataFrame:
        """
        Fetch from Yahoo Finance (unofficial)
        """
        interval_map = {
            "5m": "5m",
            "15m": "15m",
            "1D": "1d"
        }
        interval = interval_map.get(timeframe, "1d")

        # Yahoo requires range/period
        # valid ranges: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
        # valid intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo

        # Map days to range
        if days <= 5: range_str = "5d"
        elif days <= 20: range_str = "1mo"
        elif days <= 60: range_str = "60d" # Yahoo 5m limitation is usually 60d
        elif days <= 730: range_str = "2y"
        else: range_str = "5y"

        # If 5m/15m, max is 60d usually for yahoo free
        if timeframe in ["5m", "15m"] and days > 60:
            range_str = "60d" # Cap at 60d for intraday

        url = f"https://query1.finance.yahoo.com/v7/finance/download/{symbol}"

        # For intraday we might need query2 and JSON API, but download CSV endpoint often works for daily.
        # For intraday, the download CSV endpoint often defaults to daily.
        # Let's use the chart API for intraday which is more reliable for granualar data,
        # or use requests with headers mimicking browser.

        # Actually, query1.finance.yahoo.com/v8/finance/chart/{symbol} is better for intraday
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

        params = {
            "range": range_str,
            "interval": interval,
            "events": "div,split"
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }

        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        result = data['chart']['result'][0]
        meta = result['meta']
        timestamps = result['timestamp']
        quote = result['indicators']['quote'][0]

        df = pd.DataFrame({
            "timestamp": pd.to_datetime(timestamps, unit='s'),
            "open": quote['open'],
            "high": quote['high'],
            "low": quote['low'],
            "close": quote['close'],
            "volume": quote['volume']
        })

        # Handle timezone
        # Yahoo timestamps are UTC usually, but let's convert to IST
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata")

        # Drop NaNs
        df.dropna(inplace=True)

        # Filter Market Hours (Intraday only)
        if timeframe in ["5m", "15m"]:
            df.set_index("timestamp", inplace=True)
            df = MarketHours.filter_market_hours(df)
            df.reset_index(inplace=True)

        return df

    def _save_cache(self, instrument, timeframe, df):
        filename = f"{instrument}_{timeframe}.csv"
        path = os.path.join(self.cache_dir, filename)
        df.to_csv(path, index=False)

    def _load_cache(self, instrument, timeframe):
        filename = f"{instrument}_{timeframe}.csv"
        path = os.path.join(self.cache_dir, filename)
        if os.path.exists(path):
            df = pd.read_csv(path)
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                # Ensure TZ aware if not
                if df["timestamp"].dt.tz is None:
                     # Assume it was saved as string representation of IST or UTC.
                     # For simplicity, let's assume it was saved correctly.
                     # But read_csv often loses timezone.
                     # Since we saved it after converting to Asia/Kolkata, the string representation usually holds offset or is naive local time.
                     # Let's assume naive local time (IST) if no offset
                     df["timestamp"] = df["timestamp"].dt.tz_localize("Asia/Kolkata", ambiguous='infer')
            return df
        return pd.DataFrame()

if __name__ == "__main__":
    # Test
    loader = DataLoader()
    try:
        df = loader.get_data("NIFTY", "15m", 5)
        print(df.head())
        print(df.tail())
    except Exception as e:
        print(e)
