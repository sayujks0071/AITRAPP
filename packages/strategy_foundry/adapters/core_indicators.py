"""Adapter for Core Indicators"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from packages.core.indicators import IndicatorCalculator

# Global instance for reuse
_calc = IndicatorCalculator()

def compute_indicators(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    Compute indicators for the entire DataFrame (vectorized).
    NOTE: packages.core.indicators mostly returns scalar (latest value) or Series.
    We need full Series for vector backtesting.

    The core `IndicatorCalculator` methods like `_rsi` return a Series/float depending on usage.
    However, `compute_all` returns a Dict of latest values (scalars).

    We need to access the private methods or underlying logic to get full series.
    Fortunately, the core methods (`_rsi`, `_atr`, etc.) return Series/Arrays internally
    or are implemented to work on Series.

    We will wrap them here to return Series aligned with df.index.
    """

    # Core indicators class was designed for live trading (latest value),
    # but its internal methods use pandas rolling/ewm which return Series.
    # We will invoke those methods directly on the instance.

    indicators = {}

    # 1. TR (Pre-calculate for efficiency)
    tr = _calc._calculate_tr(df) # Returns np.ndarray
    indicators["tr"] = pd.Series(tr, index=df.index)

    # 2. ATR
    # Core: _atr(df, tr) -> float (latest). We need Series.
    # We copy logic or modify if possible. Core's _atr calls .iloc[-1] at end.
    # We will implement vectorized versions here reusing core logic pattern where possible
    # or just reimplement efficiently if core forces scalar return.

    # Actually, let's look at `packages.core.indicators.py`.
    # `_atr` returns `float` and calls `iloc[-1]`.
    # But inside it does `atr = pd.Series(tr).rolling(...)`.
    # So we can just replicate the vector part.

    # ATR
    atr_period = _calc.atr_period
    indicators["atr"] = indicators["tr"].rolling(window=atr_period).mean()

    # RSI
    rsi_period = _calc.rsi_period
    close = df["close"]
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    indicators["rsi"] = 100 - (100 / (1 + rs))

    # ADX
    # Reusing core logic adapted for vector return
    adx_period = _calc.adx_period
    high = df["high"]
    low = df["low"]
    up_move = high - high.shift()
    down_move = low.shift() - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    # We need ATR for ADX, but ADX usually uses Wilder's smoothing or simple rolling.
    # Core uses simple rolling.
    atr_adx = indicators["tr"].rolling(window=adx_period).mean()

    plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(window=adx_period).mean() / atr_adx
    minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(window=adx_period).mean() / atr_adx
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    indicators["adx"] = dx.rolling(window=adx_period).mean()

    # EMA
    indicators["ema_fast"] = df["close"].ewm(span=_calc.ema_fast, adjust=False).mean()
    indicators["ema_slow"] = df["close"].ewm(span=_calc.ema_slow, adjust=False).mean()

    # Supertrend
    # Core _supertrend returns (val, dir). It iterates.
    # For backtesting 5000 bars, iteration is slow but acceptable (milliseconds).
    # We can use the core method if we modify it to return array, or just copy the loop.
    # The core method `_supertrend` returns SCALAR.
    # We will copy the optimized loop here to get the full array.
    st_period = _calc.supertrend_period
    st_multiplier = _calc.supertrend_multiplier

    high_arr = df["high"].values
    low_arr = df["low"].values
    close_arr = df["close"].values

    # ATR for ST
    atr_st = indicators["tr"].rolling(window=st_period).mean().values

    hl_avg = (high_arr + low_arr) / 2
    basic_ub = hl_avg + (st_multiplier * atr_st)
    basic_lb = hl_avg - (st_multiplier * atr_st)

    n = len(df)
    final_ub = np.zeros(n)
    final_lb = np.zeros(n)
    supertrend = np.zeros(n)
    direction = np.zeros(n) # 1 or -1

    # Initialize
    final_ub[0] = basic_ub[0]
    final_lb[0] = basic_lb[0]

    # Numba would be great here, but we stick to pure python/numpy
    for i in range(1, n):
        # Final UB
        if np.isnan(final_ub[i-1]):
             final_ub[i] = basic_ub[i]
        elif (basic_ub[i] < final_ub[i-1]) or (close_arr[i-1] > final_ub[i-1]):
            final_ub[i] = basic_ub[i]
        else:
            final_ub[i] = final_ub[i-1]

        # Final LB
        if np.isnan(final_lb[i-1]):
            final_lb[i] = basic_lb[i]
        elif (basic_lb[i] > final_lb[i-1]) or (close_arr[i-1] < final_lb[i-1]):
            final_lb[i] = basic_lb[i]
        else:
            final_lb[i] = final_lb[i-1]

        # Trend
        # If prev trend was down (-1)
        if direction[i-1] == -1:
            if close_arr[i] > final_ub[i]:
                direction[i] = 1
            else:
                direction[i] = -1
        # If prev trend was up (1) or init (0)
        else:
            if close_arr[i] < final_lb[i]:
                direction[i] = -1
            else:
                direction[i] = 1

        if direction[i] == 1:
            supertrend[i] = final_lb[i]
        else:
            supertrend[i] = final_ub[i]

    indicators["supertrend"] = pd.Series(supertrend, index=df.index)
    indicators["supertrend_direction"] = pd.Series(direction, index=df.index)

    # Bollinger Bands
    bb_period = _calc.bb_period
    bb_std = _calc.bb_std
    middle = df["close"].rolling(window=bb_period).mean()
    std = df["close"].rolling(window=bb_period).std()
    indicators["bb_upper"] = middle + (std * bb_std)
    indicators["bb_lower"] = middle - (std * bb_std)

    # Donchian
    dc_period = 20
    indicators["dc_upper"] = df["high"].rolling(window=dc_period).max()
    indicators["dc_lower"] = df["low"].rolling(window=dc_period).min()

    return indicators
