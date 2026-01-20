from typing import Tuple, Optional
import numpy as np
import pandas as pd
from packages.core.indicators import IndicatorCalculator

class IndicatorsAdapter:
    """
    Adapter for technical indicators.
    Reuses core logic where flexible, implements custom logic where core is rigid.
    """

    def __init__(self):
        self.core_calc = IndicatorCalculator()

    def ema(self, series: pd.Series, period: int) -> pd.Series:
        return self.core_calc.ema_series(series, period)

    def sma(self, series: pd.Series, period: int) -> pd.Series:
        return series.rolling(window=period).mean()

    def rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        # Re-implementation to allow custom period
        close = df["close"].values
        delta = np.diff(close, prepend=np.nan)

        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)

        avg_gain = self.core_calc.rolling_mean(gain, period)
        avg_loss = self.core_calc.rolling_mean(loss, period)

        with np.errstate(divide='ignore', invalid='ignore'):
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        # rolling_mean returns np array, convert to series
        return pd.Series(rsi, index=df.index)

    def atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        # Re-implementation to allow custom period
        tr = self.core_calc.calculate_tr(df)
        atr_vals = self.core_calc.rolling_mean(tr, period)
        return pd.Series(atr_vals, index=df.index)

    def donchian(self, df: pd.DataFrame, period: int = 20) -> Tuple[pd.Series, pd.Series]:
        return self.core_calc.donchian_series(df, period)

    def bollinger_bands(self, series: pd.Series, period: int = 20, std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        middle = series.rolling(window=period).mean()
        std_dev = series.rolling(window=period).std()
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        return upper, lower, middle

    def supertrend(self, df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
        # Core supertrend is rigid on params in __init__?
        # Yes, calculate_tr is generic, but supertrend_series uses self.supertrend_period/multiplier
        # So we reimplement using core structure

        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        tr = self.core_calc.calculate_tr(df)
        atr = self.core_calc.rolling_mean(tr, period)

        hl_avg = (high + low) / 2
        basic_ub = hl_avg + (multiplier * atr)
        basic_lb = hl_avg - (multiplier * atr)

        n = len(df)
        final_ub = np.zeros(n)
        final_lb = np.zeros(n)
        supertrend = np.zeros(n)
        direction = np.ones(n, dtype=int)

        # Initialize
        final_ub[0] = basic_ub[0]
        final_lb[0] = basic_lb[0]

        # Logic matches core but adapted for variable params
        # Using simple loop as in core
        for i in range(1, n):
            # UB
            if np.isnan(final_ub[i-1]):
                final_ub[i] = basic_ub[i]
            elif basic_ub[i] < final_ub[i-1] or close[i-1] > final_ub[i-1]:
                final_ub[i] = basic_ub[i]
            else:
                final_ub[i] = final_ub[i-1]

            # LB
            if np.isnan(final_lb[i-1]):
                final_lb[i] = basic_lb[i]
            elif basic_lb[i] > final_lb[i-1] or close[i-1] < final_lb[i-1]:
                final_lb[i] = basic_lb[i]
            else:
                final_lb[i] = final_lb[i-1]

            # Trend
            if close[i] <= final_ub[i]:
                supertrend[i] = final_ub[i]
                direction[i] = -1
            else:
                supertrend[i] = final_lb[i]
                direction[i] = 1

        return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)

    def adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        # Re-implement for variable period
        high = df["high"].values
        low = df["low"].values

        prev_high = np.roll(high, 1)
        prev_low = np.roll(low, 1)

        up_move = high - prev_high
        down_move = prev_low - low

        # Fix first element
        up_move[0] = 0
        down_move[0] = 0

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        tr = self.core_calc.calculate_tr(df)

        atr = self.core_calc.rolling_mean(tr, period)
        plus_dm_smooth = self.core_calc.rolling_mean(plus_dm, period)
        minus_dm_smooth = self.core_calc.rolling_mean(minus_dm, period)

        with np.errstate(divide='ignore', invalid='ignore'):
            plus_di = 100 * plus_dm_smooth / atr
            minus_di = 100 * minus_dm_smooth / atr
            dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)

        adx = self.core_calc.rolling_mean(dx, period)
        return pd.Series(adx, index=df.index)
