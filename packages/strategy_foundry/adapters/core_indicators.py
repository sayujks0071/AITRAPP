import numpy as np
import pandas as pd
from typing import Optional, Tuple

class FoundryIndicators:
    """
    Vectorized indicator calculations for Strategy Foundry backtesting.
    Returns full Series/Arrays instead of just the latest value.
    Reuses logic from core where possible/appropriate.
    """

    @staticmethod
    def calculate_tr(df: pd.DataFrame) -> np.ndarray:
        """True Range"""
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        tr1 = high - low
        prev_close = np.roll(close, 1)
        prev_close[0] = close[0] # Handle first element

        tr2 = np.abs(high - prev_close)
        tr3 = np.abs(low - prev_close)

        return np.maximum(tr1, np.maximum(tr2, tr3))

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average True Range"""
        tr = FoundryIndicators.calculate_tr(df)
        return pd.Series(tr, index=df.index).rolling(window=period).mean()

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()

        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average Directional Index"""
        high = df["high"]
        low = df["low"]

        up_move = high - high.shift()
        down_move = low.shift() - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        tr = FoundryIndicators.calculate_tr(df)
        atr = pd.Series(tr, index=df.index).ewm(alpha=1/period, adjust=False).mean()

        plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean() / atr
        minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean() / atr

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        return dx.ewm(alpha=1/period, adjust=False).mean()

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return series.rolling(window=period).mean()

    @staticmethod
    def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
        """
        Supertrend
        Returns: (supertrend_line, direction)
        direction: 1 (uptrend), -1 (downtrend)
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr = FoundryIndicators.calculate_tr(df)
        atr = pd.Series(tr, index=df.index).rolling(window=period).mean()

        hl2 = (high + low) / 2
        basic_ub = hl2 + (multiplier * atr)
        basic_lb = hl2 - (multiplier * atr)

        n = len(df)
        final_ub = np.zeros(n)
        final_lb = np.zeros(n)
        supertrend = np.zeros(n)
        direction = np.zeros(n)

        # Simple iterative implementation for correctness
        # (Vectorizing Supertrend fully is hard due to recursive dependency)
        close_vals = close.values
        bub = basic_ub.values
        blb = basic_lb.values

        # Init
        final_ub[0] = bub[0]
        final_lb[0] = blb[0]
        direction[0] = 1
        supertrend[0] = final_lb[0]

        for i in range(1, n):
            # Final UB
            if bub[i] < final_ub[i-1] or close_vals[i-1] > final_ub[i-1]:
                final_ub[i] = bub[i]
            else:
                final_ub[i] = final_ub[i-1]

            # Final LB
            if blb[i] > final_lb[i-1] or close_vals[i-1] < final_lb[i-1]:
                final_lb[i] = blb[i]
            else:
                final_lb[i] = final_lb[i-1]

            # Trend
            if direction[i-1] == 1:
                if close_vals[i] < final_lb[i]:
                    direction[i] = -1
                    supertrend[i] = final_ub[i]
                else:
                    direction[i] = 1
                    supertrend[i] = final_lb[i]
            else:
                if close_vals[i] > final_ub[i]:
                    direction[i] = 1
                    supertrend[i] = final_lb[i]
                else:
                    direction[i] = -1
                    supertrend[i] = final_ub[i]

        return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)

    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands: Upper, Middle, Lower"""
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower

    @staticmethod
    def donchian(df: pd.DataFrame, period: int = 20) -> Tuple[pd.Series, pd.Series]:
        """Donchian Channel: Upper, Lower"""
        upper = df["high"].rolling(window=period).max()
        lower = df["low"].rolling(window=period).min()
        return upper, lower
