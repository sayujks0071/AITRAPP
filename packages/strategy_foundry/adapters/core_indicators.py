"""
Adapter for core indicators to support vectorized backtesting.
Extends the core IndicatorCalculator to return full series instead of just the last value.
"""
import numpy as np
import pandas as pd
from packages.core.indicators import IndicatorCalculator

class VectorIndicatorCalculator(IndicatorCalculator):
    """
    Extends IndicatorCalculator to provide full series outputs.
    """
    def __init__(self, **kwargs):
        # Safely handle arbitrary indicator params by updating instance dict
        # This allows re-using the calculator for different strategies without hardcoding init args
        super().__init__()
        self.__dict__.update(kwargs)

    def atr_series(self, df: pd.DataFrame) -> np.ndarray:
        """Calculate ATR series"""
        tr = self._calculate_tr(df)
        atr = self._rolling_mean(tr, self.atr_period)
        return atr

    def rsi_series(self, df: pd.DataFrame) -> np.ndarray:
        """Calculate RSI series"""
        close = df["close"].values
        delta = np.diff(close, prepend=np.nan)

        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)

        avg_gain = self._rolling_mean(gain, self.rsi_period)
        avg_loss = self._rolling_mean(loss, self.rsi_period)

        with np.errstate(divide='ignore', invalid='ignore'):
             rs = avg_gain / avg_loss
             rsi = 100 - (100 / (1 + rs))

        return rsi

    def adx_series(self, df: pd.DataFrame) -> np.ndarray:
        """Calculate ADX series"""
        high = df["high"].values
        low = df["low"].values

        prev_high = np.roll(high, 1)
        prev_low = np.roll(low, 1)

        up_move = high - prev_high
        down_move = prev_low - low

        # Fix first element
        up_move[0] = np.nan
        down_move[0] = np.nan

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        tr = self._calculate_tr(df)
        atr = self._rolling_mean(tr, self.adx_period)

        plus_dm_smooth = self._rolling_mean(plus_dm, self.adx_period)
        minus_dm_smooth = self._rolling_mean(minus_dm, self.adx_period)

        with np.errstate(divide='ignore', invalid='ignore'):
            plus_di = 100 * plus_dm_smooth / atr
            minus_di = 100 * minus_dm_smooth / atr
            dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)

        adx = self._rolling_mean(dx, self.adx_period)
        return adx

    def ema_series(self, series: pd.Series, period: int) -> np.ndarray:
        """Calculate EMA series"""
        return series.ewm(span=period, adjust=False).mean().values

    def supertrend_series(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculate Supertrend series.
        Returns (supertrend_values, direction_flags)
        """
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        tr = self._calculate_tr(df)
        atr = self._rolling_mean(tr, self.supertrend_period)

        hl_avg = (high + low) / 2
        basic_ub = hl_avg + (self.supertrend_multiplier * atr)
        basic_lb = hl_avg - (self.supertrend_multiplier * atr)

        n = len(df)
        final_ub = np.zeros(n)
        final_lb = np.zeros(n)
        supertrend = np.zeros(n)
        direction = np.ones(n, dtype=int)

        # Initial values
        final_ub[0] = basic_ub[0]
        final_lb[0] = basic_lb[0]

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

        return supertrend, direction

    def bollinger_bands_series(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate Bollinger Bands series"""
        close = df["close"]
        middle = close.rolling(window=self.bb_period).mean()
        std = close.rolling(window=self.bb_period).std()
        upper = middle + (std * self.bb_std)
        lower = middle - (std * self.bb_std)
        return upper.values, middle.values, lower.values

    def donchian_series(self, df: pd.DataFrame, period: int = 20) -> tuple[np.ndarray, np.ndarray]:
        """Calculate Donchian Channel series"""
        upper = df["high"].rolling(window=period).max()
        lower = df["low"].rolling(window=period).min()
        return upper.values, lower.values
