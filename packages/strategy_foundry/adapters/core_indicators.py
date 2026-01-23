from typing import Dict, Optional
import pandas as pd
import numpy as np
from packages.core.indicators import IndicatorCalculator

class IndicatorsAdapter:
    """Adapter for core indicators to ensure interface stability and dynamic params"""
    def __init__(self):
        self.core_calc = IndicatorCalculator() # For EMA/Donchian which support dynamic params

    def donchian_series(self, df: pd.DataFrame, period: int):
        return self.core_calc.donchian_series(df, period)

    def ema_series(self, series: pd.Series, period: int):
        return self.core_calc.ema_series(series, period)

    def rsi_series(self, df: pd.DataFrame, period: int = 14):
        # Re-implementation to support dynamic period
        close = df["close"].values
        delta = np.diff(close, prepend=np.nan)

        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)

        avg_gain = self._rolling_mean(gain, period)
        avg_loss = self._rolling_mean(loss, period)

        with np.errstate(divide='ignore', invalid='ignore'):
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
        return rsi

    def atr_series(self, df: pd.DataFrame, period: int = 14):
        # Re-implementation to support dynamic period
        tr = self.core_calc.calculate_tr(df)
        return self._rolling_mean(tr, period)

    def _rolling_mean(self, arr: np.ndarray, window: int) -> np.ndarray:
        # Reuse core logic if possible or copy
        return self.core_calc.rolling_mean(arr, window)
