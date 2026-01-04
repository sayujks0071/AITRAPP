"""
Core Indicators Adapter
Wraps pandas-ta like calculations using vectorized operations.
Reuses logic from packages.core.indicators where applicable, but optimized for backtesting (series output).
"""
import pandas as pd
import numpy as np
from typing import Tuple

class Indicators:
    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(window=period).mean()

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0))
        loss = (-delta.where(delta < 0, 0))

        # Use Wilder's Smoothing (alpha = 1/n) which is equivalent to ewm(alpha=1/period, adjust=False)
        avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        # Wilder's smoothing
        return tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        up_move = high - high.shift()
        down_move = low.shift() - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        # Convert to series for ewm
        plus_dm_s = pd.Series(plus_dm, index=high.index)
        minus_dm_s = pd.Series(minus_dm, index=high.index)

        atr = Indicators.atr(high, low, close, period)

        # Smoothed DM
        plus_di = 100 * plus_dm_s.ewm(alpha=1/period, min_periods=period, adjust=False).mean() / atr
        minus_di = 100 * minus_dm_s.ewm(alpha=1/period, min_periods=period, adjust=False).mean() / atr

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        return dx.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    @staticmethod
    def bollinger_bands(series: pd.Series, period: int, std_dev: float) -> Tuple[pd.Series, pd.Series, pd.Series]:
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower

    @staticmethod
    def donchian(high: pd.Series, low: pd.Series, period: int) -> Tuple[pd.Series, pd.Series]:
        upper = high.rolling(window=period).max()
        lower = low.rolling(window=period).min()
        return upper, lower

    @staticmethod
    def supertrend(high: pd.Series, low: pd.Series, close: pd.Series, period: int, multiplier: float) -> pd.Series:
        atr = Indicators.atr(high, low, close, period)

        hl2 = (high + low) / 2
        basic_upper = hl2 + (multiplier * atr)
        basic_lower = hl2 - (multiplier * atr)

        close_np = close.values
        bu_np = basic_upper.values
        bl_np = basic_lower.values

        n = len(close)
        final_upper = np.zeros(n)
        final_lower = np.zeros(n)
        trend = np.zeros(n) # 1 for up, -1 for down

        # Initialize
        final_upper[:] = np.nan
        final_lower[:] = np.nan

        for i in range(1, n):
            if np.isnan(bu_np[i]):
                # Keep NaN
                continue

            # If previous was NaN, initialize
            if np.isnan(final_upper[i-1]):
                final_upper[i] = bu_np[i]
                final_lower[i] = bl_np[i]
                # Default trend? Assume based on close vs bands
                if close_np[i] > final_upper[i]:
                     trend[i] = 1
                elif close_np[i] < final_lower[i]:
                     trend[i] = -1
                else:
                     trend[i] = 1 # default
                continue

            # Final Upper Band
            if (bu_np[i] < final_upper[i-1]) or (close_np[i-1] > final_upper[i-1]):
                final_upper[i] = bu_np[i]
            else:
                final_upper[i] = final_upper[i-1]

            # Final Lower Band
            if (bl_np[i] > final_lower[i-1]) or (close_np[i-1] < final_lower[i-1]):
                final_lower[i] = bl_np[i]
            else:
                final_lower[i] = final_lower[i-1]

            # Trend
            if close_np[i] > final_upper[i-1]:
                trend[i] = 1
            elif close_np[i] < final_lower[i-1]:
                trend[i] = -1
            else:
                trend[i] = trend[i-1]

        # Return supertrend line based on direction
        st_line = np.where(trend == 1, final_lower, final_upper)
        # Fix: where trend is 0 (initial), it should be NaN
        st_line = np.where(trend == 0, np.nan, st_line)

        # Explicitly forward fill initial valid value if there are subsequent NaN? No, ST shouldn't have gaps once started.

        return pd.Series(st_line, index=close.index)
