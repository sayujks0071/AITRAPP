import pandas as pd
from pathlib import Path
import yaml
import structlog
from datetime import datetime, timedelta
from typing import Optional
from packages.strategy_foundry.data.sources import YahooSource

logger = structlog.get_logger(__name__)

class DataLoader:
    """Data loader with caching and instrument mapping"""

    def __init__(self, config_path: str = "packages/strategy_foundry/configs/foundry.yaml",
                 map_path: str = "packages/strategy_foundry/configs/instrument_map.yaml"):

        self.root_dir = Path(__file__).parent.parent

        # Load configs
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        with open(map_path, "r") as f:
            self.instrument_map = yaml.safe_load(f)

        self.cache_dir = Path(self.config["data"]["cache_dir"])
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.source = YahooSource()

    def get_symbol_for_research(self, instrument: str) -> Optional[str]:
        return self.instrument_map.get("research", {}).get(instrument)

    def get_ohlcv(self, instrument: str, timeframe: str, force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """
        Get OHLCV data for an instrument (e.g. NIFTY) and timeframe (e.g. 5m).
        Tries cache first, then source.
        """
        symbol = self.get_symbol_for_research(instrument)
        if not symbol:
            logger.error(f"No research symbol found for {instrument}")
            return None

        cache_file = self.cache_dir / f"{instrument}_{timeframe}.csv"

        # Check cache
        if not force_refresh and cache_file.exists():
            # Check age? For now assume valid if exists, runner will force refresh if needed
            try:
                df = pd.read_csv(cache_file, index_col="Date", parse_dates=True)
                return df
            except Exception as e:
                logger.warning(f"Failed to read cache for {instrument} {timeframe}", error=str(e))

        # Fetch from source
        yahoo_interval = timeframe
        yahoo_range = "60d" if timeframe in ["5m", "15m"] else "max"

        df = self.source.fetch_ohlcv(symbol, yahoo_interval, yahoo_range)

        if df is not None and not df.empty:
            df.to_csv(cache_file)
            return df

        # Fallback to cache if fetch failed and cache exists (even if force_refresh was True)
        if cache_file.exists():
             logger.warning(f"Fetch failed, falling back to stale cache for {instrument}")
             return pd.read_csv(cache_file, index_col="Date", parse_dates=True)

        return None
