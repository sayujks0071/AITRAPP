from packages.core.indicators import IndicatorCalculator
import pandas as pd
import numpy as np
from typing import Dict

class VectorIndicatorCalculator(IndicatorCalculator):
    """
    Adapter for core indicators ensuring vector outputs (Series/Arrays)
    for vectorized backtesting.
    """

    def __init__(self, **kwargs):
        # Allow overriding defaults
        super().__init__(**kwargs)

    def compute_vectors(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Compute all indicators as vectors aligned with df index.
        """
        indicators = {}

        # Base Helpers
        tr = self.calculate_tr(df)

        # Trend
        indicators["ema_fast"] = self.ema_series(df["close"], self.ema_fast)
        indicators["ema_slow"] = self.ema_series(df["close"], self.ema_slow)

        st_val, st_dir = self.supertrend_series(df, tr=tr)
        indicators["supertrend"] = pd.Series(st_val, index=df.index)
        indicators["supertrend_dir"] = pd.Series(st_dir, index=df.index)

        d_up, d_low = self.donchian_series(df)
        indicators["donchian_upper"] = d_up
        indicators["donchian_lower"] = d_low

        # Momentum
        indicators["rsi"] = pd.Series(self.rsi_series(df), index=df.index)

        # Volatility
        indicators["atr"] = pd.Series(self.atr_series(df, tr=tr), index=df.index)

        bb_u, bb_m, bb_l = self.bollinger_bands_series(df["close"])
        indicators["bb_upper"] = bb_u
        indicators["bb_lower"] = bb_l
        indicators["bb_width"] = (bb_u - bb_l) / bb_m

        indicators["adx"] = pd.Series(self.adx_series(df, tr=tr), index=df.index)

        return pd.DataFrame(indicators)
