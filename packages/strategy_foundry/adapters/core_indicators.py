"""Adapter for core indicators to strategy foundry.
Focuses on vectorization where possible for backtesting speed.
"""
import pandas as pd
import numpy as np

class TechnicalIndicators:
    """Vectorized indicators for backtesting"""

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        # Using Wilder's Smoothing for ATR usually, but here matching core logic style (ewm or simple rolling?)
        # Core uses simple rolling mean. Foundry prefers robustness, so we stick to simple rolling for consistency with core.
        return tr.rolling(window=period).mean()

    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        up_move = high - high.shift()
        down_move = low.shift() - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        plus_di = 100 * pd.Series(plus_dm).rolling(window=period).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).rolling(window=period).mean() / atr

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        return dx.rolling(window=period).mean()

    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0):
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower

    @staticmethod
    def donchian(high: pd.Series, low: pd.Series, period: int = 20):
        upper = high.rolling(window=period).max()
        lower = low.rolling(window=period).min()
        return upper, lower

    @staticmethod
    def supertrend(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 10, multiplier: float = 3.0) -> tuple[pd.Series, pd.Series]:
        """
        Vectorized supertrend calculation.
        Returns: (supertrend_line, direction)
        """
        # Calculate ATR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        hl2 = (high + low) / 2
        basic_upper = hl2 + (multiplier * atr)
        basic_lower = hl2 - (multiplier * atr)

        # Numba or Cython would be better here, but we stick to pure python/pandas/numpy
        # Iterative calculation is required for Supertrend definition
        n = len(close)
        st = np.zeros(n)
        direction = np.zeros(n)
        final_upper = np.zeros(n)
        final_lower = np.zeros(n)

        # Pre-convert to numpy arrays for speed
        close_arr = close.values
        bu_arr = basic_upper.values
        bl_arr = basic_lower.values

        for i in range(1, n):
            if np.isnan(bu_arr[i]):
                continue

            # Final Upper
            if bu_arr[i] < final_upper[i-1] or close_arr[i-1] > final_upper[i-1]:
                final_upper[i] = bu_arr[i]
            else:
                final_upper[i] = final_upper[i-1]

            # Final Lower
            if bl_arr[i] > final_lower[i-1] or close_arr[i-1] < final_lower[i-1]:
                final_lower[i] = bl_arr[i]
            else:
                final_lower[i] = final_lower[i-1]

            # Trend
            if st[i-1] == final_upper[i-1] and close_arr[i] <= final_upper[i]:
                st[i] = final_upper[i]
                direction[i] = -1
            elif st[i-1] == final_upper[i-1] and close_arr[i] > final_upper[i]:
                st[i] = final_lower[i]
                direction[i] = 1
            elif st[i-1] == final_lower[i-1] and close_arr[i] >= final_lower[i]:
                st[i] = final_lower[i]
                direction[i] = 1
            elif st[i-1] == final_lower[i-1] and close_arr[i] < final_lower[i]:
                st[i] = final_upper[i]
                direction[i] = -1
            else:
                # Initialization
                st[i] = final_lower[i]
                direction[i] = 1

        return pd.Series(st, index=close.index), pd.Series(direction, index=close.index)
