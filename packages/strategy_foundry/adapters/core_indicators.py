"""Adapter for Core Indicators"""
import pandas as pd
from typing import Dict, Optional
from packages.core.indicators import IndicatorCalculator

class CoreIndicatorAdapter:
    def __init__(self):
        self.calculator = IndicatorCalculator()

    def compute_all(self, df: pd.DataFrame) -> Dict[str, Optional[float]]:
        """
        Compute all indicators using the core calculator.
        Note: The core calculator computes only the LATEST value.
        For backtesting, we often need the full series.

        This adapter will expand to provide full series calculation if needed,
        or we can just reuse the internal methods of IndicatorCalculator if they were public/static.

        Since IndicatorCalculator methods like _ema return a single float (latest value)
        BUT compute on the whole series internally, we might need to subclass or copy logic
        if we want vectorization for backtesting.

        However, for the 'strategy grammar' which might run row-by-row or vectorized,
        let's implement vectorized versions here using pandas directly for efficiency in backtests,
        while keeping names consistent.
        """
        return self.calculator.compute_all(df)

    # Vectorized implementations for backtesting efficiency

    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(window=period).mean()

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    @staticmethod
    def supertrend(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 10, multiplier: float = 3.0) -> pd.Series:
        """
        Vectorized Supertrend calculation.
        Returns the Supertrend line.
        """
        # Calculate ATR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        hl2 = (high + low) / 2
        basic_upperband = hl2 + (multiplier * atr)
        basic_lowerband = hl2 - (multiplier * atr)

        # Initialize final bands
        final_upperband = basic_upperband.copy()
        final_lowerband = basic_lowerband.copy()

        # We still need a loop for the recursive nature of Supertrend,
        # but we can try to minimize it or use Numba if available (but Numba is not allowed per plan constraints).
        # We will use a standard loop.

        trend = pd.Series(1, index=close.index) # 1 for up, -1 for down
        supertrend = pd.Series(0.0, index=close.index)

        for i in range(1, len(close)):
            if basic_upperband.iloc[i] < final_upperband.iloc[i-1] or close.iloc[i-1] > final_upperband.iloc[i-1]:
                final_upperband.iloc[i] = basic_upperband.iloc[i]
            else:
                final_upperband.iloc[i] = final_upperband.iloc[i-1]

            if basic_lowerband.iloc[i] > final_lowerband.iloc[i-1] or close.iloc[i-1] < final_lowerband.iloc[i-1]:
                final_lowerband.iloc[i] = basic_lowerband.iloc[i]
            else:
                final_lowerband.iloc[i] = final_lowerband.iloc[i-1]

            if trend.iloc[i-1] == 1:
                if close.iloc[i] <= final_upperband.iloc[i]:
                    trend.iloc[i] = -1
                    supertrend.iloc[i] = final_upperband.iloc[i]
                else:
                    trend.iloc[i] = 1
                    supertrend.iloc[i] = final_lowerband.iloc[i]
            else:
                if close.iloc[i] >= final_lowerband.iloc[i]:
                    trend.iloc[i] = 1
                    supertrend.iloc[i] = final_lowerband.iloc[i]
                else:
                    trend.iloc[i] = -1
                    supertrend.iloc[i] = final_upperband.iloc[i]

        return supertrend

    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower

    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        up_move = high - high.shift()
        down_move = low.shift() - low

        plus_dm = pd.Series(0.0, index=high.index)
        minus_dm = pd.Series(0.0, index=high.index)

        plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
        minus_dm[(down_move > up_move) & (down_move > 0)] = down_move

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        plus_di = 100 * plus_dm.rolling(window=period).mean() / atr
        minus_di = 100 * minus_dm.rolling(window=period).mean() / atr

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        return dx.rolling(window=period).mean()
