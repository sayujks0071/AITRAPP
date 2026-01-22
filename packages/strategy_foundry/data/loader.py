import pandas as pd
import structlog
from pathlib import Path
from typing import Optional
from packages.strategy_foundry.data.sources import YahooSource

logger = structlog.get_logger(__name__)

class DataLoader:
    """
    Loads and caches OHLCV data.
    """

    def __init__(self, cache_dir: str = "packages/strategy_foundry/data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.source = YahooSource()

    def get_data(self, symbol: str, timeframe: str, force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """
        Get data for symbol and timeframe.
        Tries cache first, unless force_refresh is True.
        """
        # Normalize timeframe for filename
        tf_map = {
            "5m": "5m",
            "15m": "15m",
            "1d": "1d",
            "1D": "1d"
        }
        tf_norm = tf_map.get(timeframe, timeframe)

        cache_file = self.cache_dir / f"{symbol.replace('^', '')}_{tf_norm}.csv"

        # Try loading from cache
        if not force_refresh and cache_file.exists():
            try:
                df = pd.read_csv(cache_file, index_col="timestamp", parse_dates=True)
                # Ensure timezone awareness if lost (CSV doesn't store TZ perfectly usually)
                if df.index.tz is None:
                    df.index = df.index.tz_localize("Asia/Kolkata")
                else:
                    df.index = df.index.tz_convert("Asia/Kolkata")

                logger.info(f"Loaded {symbol} {timeframe} from cache")
                return df
            except Exception as e:
                logger.warning(f"Failed to load cache for {symbol}: {e}")

        # Fetch from source
        # Determine range based on timeframe
        range_map = {
            "5m": "60d",
            "15m": "60d",
            "1d": "5y" # 5 years for daily sanity
        }
        range_str = range_map.get(tf_norm, "1mo")

        df = self.source.fetch(symbol, tf_norm, range_str)

        if df is not None and not df.empty:
            # Save to cache
            df.to_csv(cache_file)
            logger.info(f"Cached {symbol} {timeframe}")

        return df

    def update_all(self, instruments: dict, timeframes: list):
        """
        Update cache for all instruments and timeframes.
        instruments: dict of name -> symbol (e.g. {'NIFTY': '^NSEI'})
        """
        for name, symbol in instruments.items():
            for tf in timeframes:
                self.get_data(symbol, tf, force_refresh=True)
