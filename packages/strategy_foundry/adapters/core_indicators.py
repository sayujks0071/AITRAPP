"""
Core indicators adapter for Strategy Foundry.
Reimplements some indicators for vectorized backtesting logic where core uses iterative logic.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple

def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all available indicators and return as a DataFrame with same index.
    """
    indicators = df.copy()

    # EMAs
    indicators['ema_34'] = ema(df['close'], 34)
    indicators['ema_89'] = ema(df['close'], 89)
    indicators['ema_20'] = ema(df['close'], 20)
    indicators['ema_50'] = ema(df['close'], 50)
    indicators['ema_200'] = ema(df['close'], 200)

    # RSI
    indicators['rsi_14'] = rsi(df['close'], 14)

    # ADX
    adx_series = adx(df, 14)
    indicators['adx_14'] = adx_series

    # ATR
    indicators['atr_14'] = atr(df, 14)

    # Bollinger Bands
    upper, mid, lower = bollinger_bands(df['close'], 20, 2.0)
    indicators['bb_upper'] = upper
    indicators['bb_middle'] = mid
    indicators['bb_lower'] = lower

    # Supertrend
    st, direction = supertrend(df, 10, 3.0)
    indicators['supertrend'] = st
    indicators['supertrend_direction'] = direction

    # Donchian
    dc_upper, dc_lower = donchian(df, 20)
    indicators['dc_upper'] = dc_upper
    indicators['dc_lower'] = dc_lower

    return indicators

def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average"""
    return series.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index with Wilder's Smoothing"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))

    # Wilder's Smoothing using ewm with alpha=1/period
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range with Wilder's Smoothing"""
    high = df['high']
    low = df['low']
    close = df['close']

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Wilder's Smoothing
    return tr.ewm(alpha=1/period, adjust=False).mean()

def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average Directional Index with Wilder's Smoothing"""
    high = df['high']
    low = df['low']
    close = df['close']

    up_move = high - high.shift()
    down_move = low.shift() - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    plus_dm = pd.Series(plus_dm, index=df.index)
    minus_dm = pd.Series(minus_dm, index=df.index)

    # Smoothed DM
    plus_dm_smooth = plus_dm.ewm(alpha=1/period, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(alpha=1/period, adjust=False).mean()

    # Smoothed ATR
    atr_smooth = atr(df, period)

    plus_di = 100 * plus_dm_smooth / atr_smooth
    minus_di = 100 * minus_dm_smooth / atr_smooth

    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    return dx.ewm(alpha=1/period, adjust=False).mean()

def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands"""
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return upper, middle, lower

def donchian(df: pd.DataFrame, period: int = 20) -> Tuple[pd.Series, pd.Series]:
    """Donchian Channel"""
    upper = df['high'].rolling(window=period).max()
    lower = df['low'].rolling(window=period).min()
    return upper, lower

def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
    """
    Supertrend indicator.
    Vectorized implementation isn't straightforward due to recursive nature,
    but we can optimize. For now, using the iterative approach from core
    but wrapped to return full series.
    """
    # Reusing logic from core but ensuring we return Series
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values

    # Calculate TR
    tr1 = high - low
    tr2 = np.abs(high - np.roll(close, 1))
    tr3 = np.abs(low - np.roll(close, 1))
    tr2[0] = tr1[0]
    tr3[0] = tr1[0]
    tr = np.maximum(tr1, np.maximum(tr2, tr3))

    # ATR
    atr = pd.Series(tr).ewm(alpha=1/period, adjust=False).mean().values

    hl_avg = (high + low) / 2
    basic_ub = hl_avg + (multiplier * atr)
    basic_lb = hl_avg - (multiplier * atr)

    n = len(df)
    final_ub = np.zeros(n)
    final_lb = np.zeros(n)
    supertrend = np.zeros(n)
    direction = np.ones(n, dtype=int)

    final_ub[0] = basic_ub[0]
    final_lb[0] = basic_lb[0]

    for i in range(1, n):
        if np.isnan(final_ub[i-1]):
            final_ub[i] = basic_ub[i]
        elif (basic_ub[i] < final_ub[i-1]) or (close[i-1] > final_ub[i-1]):
            final_ub[i] = basic_ub[i]
        else:
            final_ub[i] = final_ub[i-1]

        if np.isnan(final_lb[i-1]):
            final_lb[i] = basic_lb[i]
        elif (basic_lb[i] > final_lb[i-1]) or (close[i-1] < final_lb[i-1]):
            final_lb[i] = basic_lb[i]
        else:
            final_lb[i] = final_lb[i-1]

        if close[i] <= final_ub[i]:
            supertrend[i] = final_ub[i]
            direction[i] = -1
        else:
            supertrend[i] = final_lb[i]
            direction[i] = 1

    return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)
