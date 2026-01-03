import pandas as pd
import structlog
from pathlib import Path
from datetime import datetime, timedelta
import os
from typing import Optional, Dict
from packages.strategy_foundry.data.sources import download_yahoo_ohlcv
from packages.strategy_foundry.configs.instrument_map import map_instrument

logger = structlog.get_logger(__name__)

CACHE_DIR = Path("packages/strategy_foundry/data/cache")

class DataLoader:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_data(self, symbol: str, timeframe: str, refresh: bool = False) -> pd.DataFrame:
        """
        Get OHLCV data for a symbol and timeframe.

        Args:
            symbol: Symbol identifier (e.g. NIFTY)
            timeframe: 5m, 15m, 1d
            refresh: If True, force download

        Returns:
            DataFrame with Open, High, Low, Close, Volume
        """
        # Map symbol to Yahoo symbol
        # For now, assume map_instrument logic or direct mapping
        # Let's read the map

        yahoo_symbol = self._get_yahoo_symbol(symbol)
        if not yahoo_symbol:
            logger.error(f"No Yahoo symbol found for {symbol}")
            return pd.DataFrame()

        cache_file = self.cache_dir / f"{symbol}_{timeframe}.csv"

        if not refresh and cache_file.exists():
            # Check age
            mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
            age = datetime.now() - mtime
            # For intraday, if cache is older than 15 mins during market hours, refresh?
            # Simplified: just use cache unless refresh=True
            logger.info(f"Loading {symbol} {timeframe} from cache")
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return df

        # Download
        logger.info(f"Downloading {symbol} {timeframe}")
        period = "max"
        if timeframe in ["5m", "15m"]:
            period = "59d" # Yahoo limitation for intraday

        df = download_yahoo_ohlcv(yahoo_symbol, interval=timeframe, period=period)

        if df is not None and not df.empty:
            df.to_csv(cache_file)
            return df

        if cache_file.exists():
             logger.warning(f"Download failed, using stale cache for {symbol}")
             return pd.read_csv(cache_file, index_col=0, parse_dates=True)

        return pd.DataFrame()

    def _get_yahoo_symbol(self, symbol: str) -> Optional[str]:
        # Simple hardcoded map or load from yaml
        # Loading from yaml every time might be slow, but it's fine for now
        # Ideally we inject config
        import yaml
        try:
            with open("packages/strategy_foundry/configs/instrument_map.yaml") as f:
                config = yaml.safe_load(f)
                return config.get("research", {}).get(symbol)
        except Exception:
            return None

