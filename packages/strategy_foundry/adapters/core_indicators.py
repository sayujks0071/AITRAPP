"""
Vectorized indicator calculations adapted from core.
Returns full Series/Arrays instead of scalar values for backtesting.
"""
import numpy as np
import pandas as pd
from typing import Tuple, Optional

class VectorizedIndicators:
    @staticmethod
    def calculate_tr(df: pd.DataFrame) -> np.ndarray:
        """Calculate True Range vector."""
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        tr1 = high - low
        prev_close = np.roll(close, 1)
        tr2 = np.abs(high - prev_close)
        tr3 = np.abs(low - prev_close)

        # First element fix
        tr2[0] = tr1[0]
        tr3[0] = tr1[0]

        return np.maximum(tr1, np.maximum(tr2, tr3))

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Vectorized ATR."""
        tr = VectorizedIndicators.calculate_tr(df)
        return pd.Series(tr, index=df.index).rolling(window=period).mean()

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Vectorized RSI."""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Vectorized ADX."""
        high = df["high"]
        low = df["low"]
        tr = VectorizedIndicators.calculate_tr(df)
        atr = pd.Series(tr, index=df.index).rolling(window=period).mean()

        up_move = high - high.shift()
        down_move = low.shift() - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(window=period).mean() / atr
        minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(window=period).mean() / atr

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        return dx.rolling(window=period).mean()

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """Vectorized EMA."""
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
        """
        Vectorized Supertrend.
        Returns (supertrend_value, direction).
        """
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        tr = VectorizedIndicators.calculate_tr(df)
        atr = pd.Series(tr).rolling(window=period).mean().values

        hl_avg = (high + low) / 2
        basic_ub = hl_avg + (multiplier * atr)
        basic_lb = hl_avg - (multiplier * atr)

        n = len(df)
        final_ub = np.zeros(n)
        final_lb = np.zeros(n)
        supertrend = np.zeros(n)
        direction = np.ones(n, dtype=int)

        # Initialize (avoid NaN issues for first period)
        final_ub[0] = basic_ub[0]
        final_lb[0] = basic_lb[0]

        # Iterative calculation (numba would be better but keeping it simple/compatible)
        for i in range(1, n):
            # Final Upper Band
            if np.isnan(final_ub[i-1]):
                 final_ub[i] = basic_ub[i]
            elif (basic_ub[i] < final_ub[i-1]) or (close[i-1] > final_ub[i-1]):
                final_ub[i] = basic_ub[i]
            else:
                final_ub[i] = final_ub[i-1]

            # Final Lower Band
            if np.isnan(final_lb[i-1]):
                final_lb[i] = basic_lb[i]
            elif (basic_lb[i] > final_lb[i-1]) or (close[i-1] < final_lb[i-1]):
                final_lb[i] = basic_lb[i]
            else:
                final_lb[i] = final_lb[i-1]

            # Supertrend
            if close[i] <= final_ub[i]:
                supertrend[i] = final_ub[i]
                direction[i] = -1
            else:
                supertrend[i] = final_lb[i]
                direction[i] = 1

        return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)

    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Vectorized Bollinger Bands."""
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower

    @staticmethod
    def donchian(df: pd.DataFrame, period: int = 20) -> Tuple[pd.Series, pd.Series]:
        """Vectorized Donchian Channels."""
        upper = df["high"].rolling(window=period).max()
        lower = df["low"].rolling(window=period).min()
        return upper, lower
