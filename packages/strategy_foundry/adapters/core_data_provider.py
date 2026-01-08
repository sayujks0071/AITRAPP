"""
Core Data Provider Adapter
"""
from typing import Optional
import pandas as pd

class CoreDataProvider:
    @staticmethod
    def get_ohlcv(symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """
        Placeholder for core data provider.
        Currently returns None to force fallback to Yahoo.
        """
        return None
