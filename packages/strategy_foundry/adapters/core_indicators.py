"""
Adapter for core indicators.
"""
from typing import Optional
import pandas as pd
import numpy as np
import structlog
from packages.core.indicators import IndicatorCalculator

logger = structlog.get_logger(__name__)

class IndicatorsAdapter:
    """
    Wraps packages.core.indicators.IndicatorCalculator to provide a consistent interface
    for StrategyFoundry.
    """

    @staticmethod
    def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates all standard indicators used by the foundry.
        Mutates the dataframe.
        """
        # StrategyFoundry uses column names like 'ema_10', 'rsi_14'.
        # Core IndicatorCalculator computes a dictionary of LATEST values usually,
        # but looking at its methods like _ema, _rsi, they return scalar (latest).
        # WAIT. The core implementation of `compute_all` returns `float` (latest value).
        # But the internal methods like `_ema` use `rolling` so they compute the whole series first.
        # However, `IndicatorCalculator` seems designed to return ONLY the latest snapshot for live trading?

        # Checking `_ema` implementation in core:
        # ema = series.ewm(...).mean()
        # return float(ema.iloc[-1])

        # This is bad for backtesting. We need the Series.
        # We cannot use IndicatorCalculator.compute_all directly for backtesting history.
        # We must re-implement vectorised calculation here or modify core to return series.
        # Since I cannot easily change core signature without risk,
        # and "Adapter" implies adapting, I will re-implement using standard pandas
        # OR see if I can use the private methods of IndicatorCalculator if they return series?
        # No, they return float.

        # So I have to implement the indicators myself here using pandas,
        # essentially duplicating logic but ensuring it matches the "style".
        # This is safer than modifying core.

        # Rename columns to match what we need.
        if 'Close' in df.columns and 'close' not in df.columns:
            df['close'] = df['Close']
        if 'High' in df.columns and 'high' not in df.columns:
            df['high'] = df['High']
        if 'Low' in df.columns and 'low' not in df.columns:
            df['low'] = df['Low']
        if 'Volume' in df.columns and 'volume' not in df.columns:
            df['volume'] = df['Volume']

        close = df['close']
        high = df['high']
        low = df['low']

        # EMAs
        for period in [10, 20, 50, 200]:
            df[f'ema_{period}'] = close.ewm(span=period, adjust=False).mean()

        # SMAs
        for period in [50, 200]:
            df[f'sma_{period}'] = close.rolling(window=period).mean()

        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi_14'] = 100 - (100 / (1 + rs))

        # MACD
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        # Bollinger Bands (20, 2)
        middle = close.rolling(window=20).mean()
        std = close.rolling(window=20).std()
        df['bb_upper'] = middle + (std * 2)
        df['bb_middle'] = middle
        df['bb_lower'] = middle - (std * 2)

        # ATR 14
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr_14'] = tr.rolling(window=14).mean()

        # Supertrend (10, 3)
        # We need the series.
        # Basic implementation.
        st_per = 10
        st_mul = 3.0
        atr_st = tr.rolling(window=st_per).mean()
        hl2 = (high + low) / 2
        basic_ub = hl2 + (st_mul * atr_st)
        basic_lb = hl2 - (st_mul * atr_st)

        # Vectorized/Iterative calculation for Supertrend
        # Python loop is fine for daily data length
        n = len(df)
        final_ub = np.zeros(n)
        final_lb = np.zeros(n)
        supertrend = np.zeros(n)

        # We need numpy arrays
        close_arr = close.values
        bub = basic_ub.fillna(0).values
        blb = basic_lb.fillna(0).values

        # Initialize
        final_ub[0] = bub[0]
        final_lb[0] = blb[0]

        for i in range(1, n):
            # Final UB
            if bub[i] < final_ub[i-1] or close_arr[i-1] > final_ub[i-1]:
                final_ub[i] = bub[i]
            else:
                final_ub[i] = final_ub[i-1]

            # Final LB
            if blb[i] > final_lb[i-1] or close_arr[i-1] < final_lb[i-1]:
                final_lb[i] = blb[i]
            else:
                final_lb[i] = final_lb[i-1]

            # Trend
            if close_arr[i] <= final_ub[i]:
                supertrend[i] = final_ub[i]
            else:
                supertrend[i] = final_lb[i]

        df['supertrend'] = supertrend

        return df
