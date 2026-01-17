import numpy as np
import pandas as pd
from packages.core.indicators import IndicatorCalculator

class VectorIndicatorCalculator(IndicatorCalculator):
    """
    Extends Core IndicatorCalculator to expose public methods returning full arrays.
    This is necessary for vectorized backtesting where we need the entire series,
    not just the last value.
    """
    def __init__(self, **kwargs):
        # Allow dynamic override of defaults
        super().__init__(**kwargs)

    def sma_series(self, series: pd.Series, period: int) -> pd.Series:
        return series.rolling(window=period).mean()

    def tr_series(self, df: pd.DataFrame) -> np.ndarray:
        return self.calculate_tr(df)

    # Exposing internal methods as public if needed, though they are already accessible.
    # The parent class has methods like atr_series, rsi_series, etc.
    # We just ensure they are available and work as expected.

    def supertrend(self, df: pd.DataFrame, period: int = None, multiplier: float = None) -> tuple[np.ndarray, np.ndarray]:
        """
        Public wrapper for supertrend series with optional param overrides.
        """
        # Temporarily override params if provided
        orig_p = self.supertrend_period
        orig_m = self.supertrend_multiplier

        if period:
            self.supertrend_period = period
        if multiplier:
            self.supertrend_multiplier = multiplier

        try:
            st, direction = self.supertrend_series(df)
            return st, direction
        finally:
            # Restore defaults
            self.supertrend_period = orig_p
            self.supertrend_multiplier = orig_m
