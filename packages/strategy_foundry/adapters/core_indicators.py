import pandas as pd
import numpy as np

def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high - high.shift()
    down_move = low.shift() - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1/period, adjust=False).mean()

    plus_di = 100 * pd.Series(plus_dm).ewm(alpha=1/period, adjust=False).mean() / atr
    minus_di = 100 * pd.Series(minus_dm).ewm(alpha=1/period, adjust=False).mean() / atr

    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    return adx

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    return tr.ewm(alpha=1/period, adjust=False).mean()

def calculate_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> tuple[pd.Series, pd.Series]:
    high = df["high"]
    low = df["low"]
    close = df["close"]

    # Calculate ATR
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()

    hl_avg = (high + low) / 2
    basic_ub = hl_avg + (multiplier * atr)
    basic_lb = hl_avg - (multiplier * atr)

    # We need to iterate for Supertrend as it is recursive
    n = len(df)
    final_ub = np.zeros(n)
    final_lb = np.zeros(n)
    supertrend = np.zeros(n)
    direction = np.zeros(n) # 1: up, -1: down

    close_vals = close.values
    bub_vals = basic_ub.values
    blb_vals = basic_lb.values

    # Initialize
    final_ub[0] = bub_vals[0]
    final_lb[0] = blb_vals[0]
    direction[0] = 1

    for i in range(1, n):
        # Final Upper Band
        if (bub_vals[i] < final_ub[i-1]) or (close_vals[i-1] > final_ub[i-1]):
            final_ub[i] = bub_vals[i]
        else:
            final_ub[i] = final_ub[i-1]

        # Final Lower Band
        if (blb_vals[i] > final_lb[i-1]) or (close_vals[i-1] < final_lb[i-1]):
            final_lb[i] = blb_vals[i]
        else:
            final_lb[i] = final_lb[i-1]

        # Trend
        # If currently in downtrend (dir=-1)
        if direction[i-1] == -1:
            if close_vals[i] > final_ub[i]:
                direction[i] = 1
            else:
                direction[i] = -1
        else: # uptrend
            if close_vals[i] < final_lb[i]:
                direction[i] = -1
            else:
                direction[i] = 1

        if direction[i] == 1:
            supertrend[i] = final_lb[i]
        else:
            supertrend[i] = final_ub[i]

    return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)

def calculate_bollinger_bands(series: pd.Series, period: int = 20, std: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    middle = series.rolling(window=period).mean()
    std_dev = series.rolling(window=period).std()
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    return upper, middle, lower

def calculate_donchian(df: pd.DataFrame, period: int = 20) -> tuple[pd.Series, pd.Series]:
    upper = df["high"].rolling(window=period).max()
    lower = df["low"].rolling(window=period).min()
    return upper, lower
