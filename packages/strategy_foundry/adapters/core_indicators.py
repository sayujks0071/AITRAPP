import numpy as np
import pandas as pd

from packages.core.indicators import IndicatorCalculator


class VectorIndicatorCalculator(IndicatorCalculator):
    """
    Adapter for core IndicatorCalculator to support vectorized backtesting
    with dynamic parameters per call.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def rsi(self, df: pd.DataFrame, period: int) -> np.ndarray:
        # Save state
        old_period = self.rsi_period
        # Set new state
        self.rsi_period = period
        try:
            return self.rsi_series(df)
        finally:
            # Restore state
            self.rsi_period = old_period

    def atr(self, df: pd.DataFrame, period: int) -> np.ndarray:
        old_period = self.atr_period
        self.atr_period = period
        try:
            return self.atr_series(df)
        finally:
            self.atr_period = old_period

    def adx(self, df: pd.DataFrame, period: int) -> np.ndarray:
        old_period = self.adx_period
        self.adx_period = period
        try:
            return self.adx_series(df)
        finally:
            self.adx_period = old_period

    def ema(self, series: pd.Series, period: int) -> pd.Series:
        # Base class _ema uses self.ema_fast/slow but ema_series takes period arg?
        # Let's check base class.
        # def ema_series(self, series: pd.Series, period: int) -> pd.Series:
        # It takes period! So we can just call it.
        return self.ema_series(series, period)

    def sma(self, series: pd.Series, period: int) -> pd.Series:
        return series.rolling(window=period).mean()

    def bollinger_bands(self, series: pd.Series, period: int, std: float) -> tuple[pd.Series, pd.Series, pd.Series]:
        old_period = self.bb_period
        old_std = self.bb_std
        self.bb_period = period
        self.bb_std = std
        try:
            return self.bollinger_bands_series(series)
        finally:
            self.bb_period = old_period
            self.bb_std = old_std

    def donchian(self, df: pd.DataFrame, period: int) -> tuple[pd.Series, pd.Series]:
        # donchian_series takes period arg
        return self.donchian_series(df, period)

    def supertrend(self, df: pd.DataFrame, period: int, multiplier: float) -> tuple[np.ndarray, np.ndarray]:
        old_period = self.supertrend_period
        old_mult = self.supertrend_multiplier
        self.supertrend_period = period
        self.supertrend_multiplier = multiplier
        try:
            return self.supertrend_series(df)
        finally:
            self.supertrend_period = old_period
            self.supertrend_multiplier = old_mult
