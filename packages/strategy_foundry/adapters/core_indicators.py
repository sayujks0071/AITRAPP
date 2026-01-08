"""
Vectorized technical indicators adapter.
Re-implements core indicators logic using vectorized operations for backtesting efficiency.
Returns full Series/DataFrames instead of single values.
"""
from typing import Optional, Tuple, Dict
import pandas as pd
import numpy as np
from packages.core.indicators import IndicatorCalculator

def calculate_tr(df: pd.DataFrame) -> pd.Series:
    """Calculate True Range (Vectorized)"""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    # TR1: High - Low
    tr1 = high - low

    # TR2: |High - PrevClose|
    tr2 = (high - close.shift(1)).abs()

    # TR3: |Low - PrevClose|
    tr3 = (low - close.shift(1)).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr

def atr(df: pd.DataFrame, period: int = 14, tr: Optional[pd.Series] = None) -> pd.Series:
    """Average True Range (Vectorized)"""
    if tr is None:
        tr = calculate_tr(df)
    return tr.rolling(window=period).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (Vectorized)"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    return 100 - (100 / (1 + rs))

def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average (Vectorized)"""
    return series.ewm(span=period, adjust=False).mean()

def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average (Vectorized)"""
    return series.rolling(window=period).mean()

def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands (Vectorized) -> (upper, middle, lower)"""
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return upper, middle, lower

def donchian_channel(df: pd.DataFrame, period: int = 20) -> Tuple[pd.Series, pd.Series]:
    """Donchian Channel (Vectorized) -> (upper, lower)"""
    upper = df["high"].rolling(window=period).max()
    lower = df["low"].rolling(window=period).min()
    return upper, lower

def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0, tr: Optional[pd.Series] = None) -> Tuple[pd.Series, pd.Series]:
    """
    Supertrend Indicator (Vectorized + Numba/Loop optimized).
    Returns (supertrend_line, direction)
    Direction: 1 (Up), -1 (Down)
    """
    # Reuse core logic via IndicatorCalculator's method logic if possible,
    # but here we need a full series.
    # Implementing the same loop as core but returning series.

    high = df["high"].values
    low = df["low"].values
    close = df["close"].values

    if tr is None:
        tr_vals = calculate_tr(df).values
    else:
        tr_vals = tr.values

    # ATR
    atr = pd.Series(tr_vals).rolling(window=period).mean().values

    hl_avg = (high + low) / 2
    basic_ub = hl_avg + (multiplier * atr)
    basic_lb = hl_avg - (multiplier * atr)

    n = len(df)
    final_ub = np.zeros(n)
    final_lb = np.zeros(n)
    st = np.zeros(n)
    direction = np.zeros(n) # 1: up, -1: down

    # Initialize
    final_ub[0] = basic_ub[0]
    final_lb[0] = basic_lb[0]
    direction[0] = 1

    for i in range(1, n):
        # Final Upper Band
        if np.isnan(basic_ub[i]):
             final_ub[i] = np.nan
        else:
            if (basic_ub[i] < final_ub[i-1]) or (close[i-1] > final_ub[i-1]):
                final_ub[i] = basic_ub[i]
            else:
                final_ub[i] = final_ub[i-1]

        # Final Lower Band
        if np.isnan(basic_lb[i]):
            final_lb[i] = np.nan
        else:
            if (basic_lb[i] > final_lb[i-1]) or (close[i-1] < final_lb[i-1]):
                final_lb[i] = basic_lb[i]
            else:
                final_lb[i] = final_lb[i-1]

        # Supertrend
        if np.isnan(final_ub[i]) or np.isnan(final_lb[i]):
            st[i] = np.nan
        else:
            prev_dir = direction[i-1] if i > 0 else 1

            if prev_dir == 1:
                if close[i] < final_lb[i]:
                    direction[i] = -1
                    st[i] = final_ub[i]
                else:
                    direction[i] = 1
                    st[i] = final_lb[i]
            else:
                if close[i] > final_ub[i]:
                    direction[i] = 1
                    st[i] = final_lb[i]
                else:
                    direction[i] = -1
                    st[i] = final_ub[i]

    return pd.Series(st, index=df.index), pd.Series(direction, index=df.index)

def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ADX (Vectorized)"""
    high = df["high"]
    low = df["low"]

    up = high - high.shift(1)
    down = low.shift(1) - low

    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)

    tr = calculate_tr(df)
    atr_val = tr.rolling(window=period).mean()

    plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(window=period).mean() / atr_val
    minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(window=period).mean() / atr_val

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.rolling(window=period).mean()
