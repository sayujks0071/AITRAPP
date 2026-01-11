import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple

class VectorizedIndicatorCalculator:
    """
    Calculates technical indicators returning full Series/Arrays.
    Based on packages.core.indicators.IndicatorCalculator logic but exposing full history.
    """

    def _rolling_mean(self, arr: np.ndarray, window: int) -> np.ndarray:
        n = len(arr)
        if n < window:
             return np.full(n, np.nan)
        kernel = np.ones(window) / window
        result = np.convolve(arr, kernel, mode='valid')
        pad = np.full(window - 1, np.nan)
        return np.concatenate((pad, result))

    def tr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
        tr1 = high - low
        prev_close = np.roll(close, 1)
        prev_close[0] = close[0] # Handle first element approx
        tr2 = np.abs(high - prev_close)
        tr3 = np.abs(low - prev_close)
        return np.maximum(tr1, np.maximum(tr2, tr3))

    def atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        tr = self.tr(high, low, close)
        # Use EWM for ATR usually? Core uses rolling mean. I will stick to Core logic.
        return self._rolling_mean(tr, period)

    def rsi(self, close: np.ndarray, period: int = 14) -> np.ndarray:
        delta = np.diff(close, prepend=np.nan)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)

        # Wilder's Smoothing is standard for RSI, but Core used rolling mean.
        # Wait, Core's `_rsi` implementation uses `_rolling_mean` which is SMA.
        # This is not Wilder's RSI. But I must reuse Core logic as requested.
        # Wait, usually RSI uses Wilder's smoothing.
        # But `IndicatorCalculator._rsi` calls `_rolling_mean`.
        # I will stick to what Core does: SMA based RSI.

        avg_gain = self._rolling_mean(gain, period)
        avg_loss = self._rolling_mean(loss, period)

        with np.errstate(divide='ignore', invalid='ignore'):
             rs = avg_gain / avg_loss
             rsi = 100 - (100 / (1 + rs))

        return rsi

    def adx(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        tr = self.tr(high, low, close)
        atr = self._rolling_mean(tr, period)

        prev_high = np.roll(high, 1)
        prev_low = np.roll(low, 1)
        up_move = high - prev_high
        down_move = prev_low - low

        # First element fix
        up_move[0] = 0
        down_move[0] = 0

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        plus_dm_smooth = self._rolling_mean(plus_dm, period)
        minus_dm_smooth = self._rolling_mean(minus_dm, period)

        with np.errstate(divide='ignore', invalid='ignore'):
            plus_di = 100 * plus_dm_smooth / atr
            minus_di = 100 * minus_dm_smooth / atr
            dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)

        adx = self._rolling_mean(dx, period)
        return adx

    def ema(self, series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def sma(self, series: pd.Series, period: int) -> pd.Series:
        return series.rolling(window=period).mean()

    def bollinger_bands(self, series: pd.Series, period: int = 20, std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        middle = series.rolling(window=period).mean()
        sigma = series.rolling(window=period).std()
        upper = middle + (sigma * std)
        lower = middle - (sigma * std)
        return upper, middle, lower

    def donchian(self, high: pd.Series, low: pd.Series, period: int = 20) -> Tuple[pd.Series, pd.Series]:
        upper = high.rolling(window=period).max()
        lower = low.rolling(window=period).min()
        return upper, lower

    def supertrend(self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 10, multiplier: float = 3.0) -> Tuple[np.ndarray, np.ndarray]:
        # Vectorized supertrend is tricky due to recursion.
        # But `IndicatorCalculator` implements it with a loop.
        # I'll do the same loop for correctness.
        tr = self.tr(high, low, close)
        atr = self._rolling_mean(tr, period)

        hl_avg = (high + low) / 2
        basic_ub = hl_avg + (multiplier * atr)
        basic_lb = hl_avg - (multiplier * atr)

        n = len(close)
        final_ub = np.zeros(n)
        final_lb = np.zeros(n)
        supertrend = np.zeros(n)
        direction = np.ones(n, dtype=int)

        # We need to fill NaNs with something safe to avoid runtime warnings in loop comparison
        # But logic handles it.

        for i in range(1, n):
            if np.isnan(basic_ub[i]): continue

            # Final Upper Band
            if (basic_ub[i] < final_ub[i-1]) or (close[i-1] > final_ub[i-1]):
                final_ub[i] = basic_ub[i]
            else:
                final_ub[i] = final_ub[i-1]

            # Final Lower Band
            if (basic_lb[i] > final_lb[i-1]) or (close[i-1] < final_lb[i-1]):
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
