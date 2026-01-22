# Strategy Foundry
import logging
import os

import pandas as pd
import requests
import yaml

logger = logging.getLogger(__name__)

class DataLoader:
    def __init__(self, cache_dir="packages/strategy_foundry/data/cache"):
        self.cache_dir = cache_dir
        self.config_path = "packages/strategy_foundry/configs/instrument_map.yaml"
        self._load_config()
        os.makedirs(self.cache_dir, exist_ok=True)

    def _load_config(self):
        with open(self.config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.research_map = self.config.get("research", {})

    def get_symbol_for_instrument(self, instrument):
        return self.research_map.get(instrument, instrument)

    def fetch_data(self, instrument, timeframe, force_refresh=False):
        """
        Fetches OHLCV data for an instrument and timeframe.
        Prioritizes cache unless force_refresh is True.
        """
        symbol = self.get_symbol_for_instrument(instrument)
        cache_file = os.path.join(self.cache_dir, f"{instrument}_{timeframe}.csv")

        if not force_refresh and os.path.exists(cache_file):
            logger.info(f"Loading {instrument} {timeframe} from cache")
            df = pd.read_csv(cache_file, parse_dates=["datetime"], index_col="datetime")
            return df

        logger.info(f"Downloading {instrument} ({symbol}) {timeframe} from source")
        df = self._download_yahoo(symbol, timeframe)

        if df is None or df.empty:
            # Fallback to ETF Proxy
            etf_proxy = self.config.get("paper_proxy", {}).get(instrument)
            if etf_proxy and etf_proxy != symbol:
                 logger.info(f"Primary symbol failed. Falling back to ETF proxy: {etf_proxy}")
                 # Append .NS if missing and looks like a symbol (simple heuristic)
                 # Research symbols start with ^. ETF proxies usually don't.
                 if not etf_proxy.endswith(".NS") and not etf_proxy.startswith("^"):
                      etf_proxy_yahoo = etf_proxy + ".NS"
                 else:
                      etf_proxy_yahoo = etf_proxy

                 df = self._download_yahoo(etf_proxy_yahoo, timeframe)

        if df is not None and not df.empty:
            df.to_csv(cache_file)
            return df
        else:
            logger.warning(f"Failed to download data for {instrument}")
            if os.path.exists(cache_file):
                logger.info("Falling back to stale cache")
                return pd.read_csv(cache_file, parse_dates=["datetime"], index_col="datetime")
            return pd.DataFrame()

    def _download_yahoo(self, symbol, timeframe):
        # Map timeframe to Yahoo API format
        interval_map = {
            "5m": "5m",
            "15m": "15m",
            "1d": "1d"
        }

        range_map = {
            "5m": "60d",
            "15m": "60d",
            "1d": "10y"
        }

        interval = interval_map.get(timeframe)
        if not interval:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        range_val = range_map.get(timeframe)

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            "interval": interval,
            "range": range_val
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            result = data["chart"]["result"][0]
            timestamps = result["timestamp"]
            indicators = result["indicators"]["quote"][0]

            df = pd.DataFrame({
                "datetime": pd.to_datetime(timestamps, unit="s", utc=True).tz_convert("Asia/Kolkata"),
                "open": indicators["open"],
                "high": indicators["high"],
                "low": indicators["low"],
                "close": indicators["close"],
                "volume": indicators["volume"]
            })

            # Remove Timezone info to avoid future warnings with some libs, but keep it local time
            df["datetime"] = df["datetime"].dt.tz_localize(None)
            df.set_index("datetime", inplace=True)

            # Drop NaN rows
            df.dropna(inplace=True)

            # Sanity Checks
            # 1. High >= Low
            df = df[df["high"] >= df["low"]]
            # 2. High >= Open and High >= Close
            df = df[(df["high"] >= df["open"]) & (df["high"] >= df["close"])]
            # 3. Low <= Open and Low <= Close
            df = df[(df["low"] <= df["open"]) & (df["low"] <= df["close"])]
            # 4. Volume >= 0
            df = df[df["volume"] >= 0]

            # Basic Market Hours Filter (09:15 - 15:30) for intraday
            if timeframe in ["5m", "15m"]:
                df = df.between_time("09:15", "15:29") # Inclusive start, inclusive end

            return df

        except Exception as e:
            logger.error(f"Error downloading {symbol}: {e}")
            return None

if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    loader = DataLoader()
    df = loader.fetch_data("NIFTY", "15m")
    print(df.tail())
