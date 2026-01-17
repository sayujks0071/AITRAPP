from packages.core.indicators import IndicatorCalculator
import numpy as np
import pandas as pd

class VectorIndicatorCalculator(IndicatorCalculator):
    """
    Adapter for IndicatorCalculator to expose vector/series calculations clearly
    for the Strategy Foundry.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def compute_all_vectors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all indicators and return as a DataFrame aligned with input df.
        """
        if df.empty:
            return pd.DataFrame(index=df.index)

        # Pre-calculate TR
        tr = self.calculate_tr(df)

        # Calculate indicators
        indicators = pd.DataFrame(index=df.index)

        indicators['atr'] = self.atr_series(df, tr=tr)
        indicators['rsi'] = self.rsi_series(df)
        indicators['adx'] = self.adx_series(df, tr=tr)
        indicators['ema_fast'] = self.ema_series(df['close'], self.ema_fast)
        indicators['ema_slow'] = self.ema_series(df['close'], self.ema_slow)

        st_val, st_dir = self.supertrend_series(df, tr=tr)
        indicators['supertrend'] = st_val
        indicators['supertrend_direction'] = st_dir

        bb_upper, bb_middle, bb_lower = self.bollinger_bands_series(df['close'])
        indicators['bb_upper'] = bb_upper
        indicators['bb_lower'] = bb_lower

        dc_upper, dc_lower = self.donchian_series(df)
        indicators['dc_upper'] = dc_upper
        indicators['dc_lower'] = dc_lower

        return indicators

    def supertrend(self, df: pd.DataFrame, period=None, multiplier=None) -> tuple[np.ndarray, np.ndarray]:
        """
        Override/expose supertrend with optional custom params.
        """
        # Save original params
        orig_period = self.supertrend_period
        orig_mult = self.supertrend_multiplier

        if period is not None:
            self.supertrend_period = period
        if multiplier is not None:
            self.supertrend_multiplier = multiplier

        try:
            return self.supertrend_series(df)
        finally:
            # Restore
            self.supertrend_period = orig_period
            self.supertrend_multiplier = orig_mult
