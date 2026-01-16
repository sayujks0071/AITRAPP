"""Adapter for Core Indicators"""
import pandas as pd
import numpy as np
from typing import Optional

try:
    from packages.core.indicators import IndicatorCalculator
except ImportError:
    IndicatorCalculator = None

class VectorIndicatorCalculator(IndicatorCalculator if IndicatorCalculator else object):
    """
    Extends or implements indicator calculation for vectorized backtesting.
    Exposes full series instead of just the last value.
    """
    def __init__(self, **kwargs):
        if IndicatorCalculator:
            super().__init__(**kwargs)
        else:
            # Fallback if core not available (should not happen in this repo)
            self.atr_period = kwargs.get('atr_period', 14)
            self.rsi_period = kwargs.get('rsi_period', 14)
            self.adx_period = kwargs.get('adx_period', 14)
            self.ema_fast = kwargs.get('ema_fast', 34)
            self.ema_slow = kwargs.get('ema_slow', 89)
            self.supertrend_period = kwargs.get('supertrend_period', 10)
            self.supertrend_multiplier = kwargs.get('supertrend_multiplier', 3.0)
            self.bb_period = kwargs.get('bb_period', 20)
            self.bb_std = kwargs.get('bb_std', 2.0)

    # Note: The core IndicatorCalculator already has some *_series methods.
    # We will ensure all needed methods are available here.

    def calculate_tr(self, df: pd.DataFrame) -> np.ndarray:
        if hasattr(super(), 'calculate_tr'):
            return super().calculate_tr(df)

        # Fallback implementation
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        prev_close = np.roll(close, 1)
        prev_close[0] = close[0] # Approximation for first element

        tr1 = high - low
        tr2 = np.abs(high - prev_close)
        tr3 = np.abs(low - prev_close)

        return np.maximum(tr1, np.maximum(tr2, tr3))

    def ema(self, series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        if hasattr(super(), 'rsi_series') and period == self.rsi_period:
            return pd.Series(super().rsi_series(df), index=df.index)

        # Standalone calc if period differs or method missing
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        if hasattr(super(), 'atr_series') and period == self.atr_period:
             return pd.Series(super().atr_series(df), index=df.index)

        tr = self.calculate_tr(df)
        return pd.Series(tr, index=df.index).rolling(window=period).mean()

    def adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        if hasattr(super(), 'adx_series') and period == self.adx_period:
            return pd.Series(super().adx_series(df), index=df.index)

        # Fallback logic omitted for brevity, assuming core is present
        # But if we need custom period support:
        tr = self.calculate_tr(df)
        plus_dm = df['high'].diff()
        minus_dm = df['low'].diff()

        plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
        minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), -minus_dm, 0) # Note logic check

        atr = pd.Series(tr).rolling(period).mean()
        plus_di = 100 * pd.Series(plus_dm).rolling(period).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).rolling(period).mean() / atr
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        return dx.rolling(period).mean()

    def supertrend(self, df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> tuple[pd.Series, pd.Series]:
        # If parameters match core, try reuse
        if (hasattr(super(), 'supertrend_series') and
            period == self.supertrend_period and
            multiplier == self.supertrend_multiplier):
            st, direction = super().supertrend_series(df)
            return pd.Series(st, index=df.index), pd.Series(direction, index=df.index)

        # Custom implementation matching core logic
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values

        # Calculate ATR
        tr = self.calculate_tr(df)
        atr = pd.Series(tr).rolling(period).mean().values

        hl2 = (high + low) / 2
        basic_upper = hl2 + (multiplier * atr)
        basic_lower = hl2 - (multiplier * atr)

        final_upper = np.zeros(len(df))
        final_lower = np.zeros(len(df))
        supertrend = np.zeros(len(df))
        direction = np.ones(len(df)) # 1: UP, -1: DOWN

        for i in range(1, len(df)):
            if basic_upper[i] < final_upper[i-1] or close[i-1] > final_upper[i-1]:
                final_upper[i] = basic_upper[i]
            else:
                final_upper[i] = final_upper[i-1]

            if basic_lower[i] > final_lower[i-1] or close[i-1] < final_lower[i-1]:
                final_lower[i] = basic_lower[i]
            else:
                final_lower[i] = final_lower[i-1]

            if direction[i-1] == 1:
                if close[i] <= final_upper[i]:
                    direction[i] = -1
                    supertrend[i] = final_upper[i]
                else:
                    direction[i] = 1
                    supertrend[i] = final_lower[i]
            else:
                if close[i] >= final_lower[i]:
                    direction[i] = 1
                    supertrend[i] = final_lower[i]
                else:
                    direction[i] = -1
                    supertrend[i] = final_upper[i]

        return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)

    def donchian(self, df: pd.DataFrame, period: int = 20) -> tuple[pd.Series, pd.Series]:
         return df["high"].rolling(window=period).max(), df["low"].rolling(window=period).min()

