"""Vectorized indicators adapter for Foundry"""
import numpy as np
import pandas as pd
from typing import Dict, Optional

class VectorizedIndicators:
    """
    Calculates technical indicators returning full Series/Arrays.
    Adapts logic from packages.core.indicators.IndicatorCalculator for vectorized backtesting.
    """

    @staticmethod
    def _rolling_mean(arr: np.ndarray, window: int) -> np.ndarray:
        n = len(arr)
        if n < window:
             return np.full(n, np.nan)
        kernel = np.ones(window) / window
        result = np.convolve(arr, kernel, mode='valid')
        pad = np.full(window - 1, np.nan)
        return np.concatenate((pad, result))

    @staticmethod
    def _wilder_smoothing(arr: np.ndarray, window: int) -> np.ndarray:
        """
        Wilder's Smoothing (used for RSI, ATR, ADX).
        Pandas ewm(alpha=1/window, adjust=False) is equivalent.
        """
        return pd.Series(arr).ewm(alpha=1/window, adjust=False).mean().values

    @staticmethod
    def tr(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
        tr1 = high - low
        prev_close = np.roll(close, 1)
        tr2 = np.abs(high - prev_close)
        tr3 = np.abs(low - prev_close)

        # Fix first element
        tr2[0] = tr1[0]
        tr3[0] = tr1[0]

        return np.maximum(tr1, np.maximum(tr2, tr3))

    @staticmethod
    def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        tr = VectorizedIndicators.tr(high, low, close)
        # Use Wilder's smoothing for ATR standard
        return VectorizedIndicators._wilder_smoothing(tr, period)

    @staticmethod
    def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
        delta = np.diff(close, prepend=np.nan)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)

        avg_gain = VectorizedIndicators._wilder_smoothing(gain, period)
        avg_loss = VectorizedIndicators._wilder_smoothing(loss, period)

        with np.errstate(divide='ignore', invalid='ignore'):
             rs = avg_gain / avg_loss
             rsi = 100 - (100 / (1 + rs))

        # Fix division by zero cases
        rsi[avg_loss == 0] = 100
        rsi[np.isnan(avg_loss)] = np.nan

        return rsi

    @staticmethod
    def adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        prev_high = np.roll(high, 1)
        prev_low = np.roll(low, 1)

        up_move = high - prev_high
        down_move = prev_low - low

        up_move[0] = np.nan
        down_move[0] = np.nan

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        tr = VectorizedIndicators.tr(high, low, close)
        atr = VectorizedIndicators._wilder_smoothing(tr, period)

        plus_dm_smooth = VectorizedIndicators._wilder_smoothing(plus_dm, period)
        minus_dm_smooth = VectorizedIndicators._wilder_smoothing(minus_dm, period)

        with np.errstate(divide='ignore', invalid='ignore'):
            plus_di = 100 * plus_dm_smooth / atr
            minus_di = 100 * minus_dm_smooth / atr
            dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)

        adx = VectorizedIndicators._wilder_smoothing(dx, period)
        return adx

    @staticmethod
    def sma(arr: np.ndarray, period: int) -> np.ndarray:
        return VectorizedIndicators._rolling_mean(arr, period)

    @staticmethod
    def ema(arr: np.ndarray, period: int) -> np.ndarray:
        return pd.Series(arr).ewm(span=period, adjust=False).mean().values

    @staticmethod
    def bollinger_bands(arr: np.ndarray, period: int = 20, std: float = 2.0):
        series = pd.Series(arr)
        middle = series.rolling(window=period).mean()
        std_dev = series.rolling(window=period).std()
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        return upper.values, middle.values, lower.values

    @staticmethod
    def donchian(high: np.ndarray, low: np.ndarray, period: int = 20):
        upper = pd.Series(high).rolling(window=period).max().values
        lower = pd.Series(low).rolling(window=period).min().values
        return upper, lower
