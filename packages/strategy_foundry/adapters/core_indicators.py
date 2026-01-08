import pandas as pd
import numpy as np
from typing import Dict

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute technical indicators for the entire dataframe.
    Returns a DataFrame with original data + indicator columns.
    """
    df = df.copy()
    close = df["close"]
    high = df["high"]
    low = df["low"]

    # EMAs
    df["ema_10"] = close.ewm(span=10, adjust=False).mean()
    df["ema_20"] = close.ewm(span=20, adjust=False).mean()
    df["ema_50"] = close.ewm(span=50, adjust=False).mean()
    df["ema_200"] = close.ewm(span=200, adjust=False).mean()

    # RSI
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean() # Wilder's smoothing is better but this matches simple reuse
    # Note: Core uses simple rolling mean for RSI? Let's check.
    # Core: gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
    # Yes, it uses simple rolling mean.
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # ATR
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr"] = tr.rolling(window=14).mean()

    # ADX (Simplified)
    up = high - high.shift()
    down = low.shift() - low
    plus_dm = np.where((up > down) & (up > 0), up, 0)
    minus_dm = np.where((down > up) & (down > 0), down, 0)

    tr_smooth = tr.rolling(window=14).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(window=14).mean() / tr_smooth
    minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(window=14).mean() / tr_smooth
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df["adx"] = dx.rolling(window=14).mean()

    # Supertrend (Vectorized approximation or loop)
    # We'll implement a simple one.
    # Logic:
    # Basic Upper = (High + Low) / 2 + Multiplier * ATR
    # Basic Lower = (High + Low) / 2 - Multiplier * ATR
    # If Close > Final Upper[1] -> Trend = 1
    # If Close < Final Lower[1] -> Trend = -1
    # This requires a loop.
    df["supertrend"], df["supertrend_dir"] = calculate_supertrend(df, period=10, multiplier=3)

    # Donchian
    df["donchian_upper"] = high.rolling(window=20).max()
    df["donchian_lower"] = low.rolling(window=20).min()

    # Bollinger
    bb_mid = close.rolling(window=20).mean()
    bb_std = close.rolling(window=20).std()
    df["bb_upper"] = bb_mid + 2 * bb_std
    df["bb_lower"] = bb_mid - 2 * bb_std

    return df

def calculate_supertrend(df, period=10, multiplier=3):
    high = df['high']
    low = df['low']
    close = df['close']

    # Calculate ATR first
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()

    hl2 = (high + low) / 2
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr

    # Initialize arrays
    n = len(df)
    final_upper = np.zeros(n)
    final_lower = np.zeros(n)
    supertrend = np.zeros(n)
    direction = np.zeros(n) # 1: up, -1: down

    close_vals = close.values
    bu_vals = basic_upper.values
    bl_vals = basic_lower.values

    # Loop
    for i in range(1, n):
        if np.isnan(bu_vals[i]): continue

        # Upper band
        if bu_vals[i] < final_upper[i-1] or close_vals[i-1] > final_upper[i-1]:
            final_upper[i] = bu_vals[i]
        else:
            final_upper[i] = final_upper[i-1]

        # Lower band
        if bl_vals[i] > final_lower[i-1] or close_vals[i-1] < final_lower[i-1]:
            final_lower[i] = bl_vals[i]
        else:
            final_lower[i] = final_lower[i-1]

        # Trend
        # Previous direction
        prev_dir = direction[i-1] if i > 0 else 1

        if prev_dir == 1:
            if close_vals[i] < final_lower[i-1]: # Changed trend to down
                direction[i] = -1
                supertrend[i] = final_upper[i]
            else:
                direction[i] = 1
                supertrend[i] = final_lower[i]
        else:
            if close_vals[i] > final_upper[i-1]: # Changed trend to up
                direction[i] = 1
                supertrend[i] = final_lower[i]
            else:
                direction[i] = -1
                supertrend[i] = final_upper[i]

    return supertrend, direction
