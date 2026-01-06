import pandas as pd
import numpy as np

def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute technical indicators for the entire DataFrame in a vectorized manner.
    Returns a new DataFrame with indicator columns added.
    """
    df = df.copy()
    close = df['close']
    high = df['high']
    low = df['low']

    # EMAs
    df['ema_10'] = _ema(close, 10)
    df['ema_20'] = _ema(close, 20)
    df['ema_50'] = _ema(close, 50)
    df['ema_200'] = _ema(close, 200)

    # RSI
    df['rsi_14'] = _rsi(close, 14)

    # ADX
    df['adx_14'] = _adx(high, low, close, 14)

    # ATR
    df['atr_14'] = _atr(high, low, close, 14)

    # Bollinger Bands
    upper, middle, lower = _bollinger_bands(close, 20, 2.0)
    df['bb_upper'] = upper
    df['bb_middle'] = middle
    df['bb_lower'] = lower

    # Donchian Channel
    df['donchian_upper_20'] = high.rolling(window=20).max()
    df['donchian_lower_20'] = low.rolling(window=20).min()

    # Supertrend (vectorized approx or iterative)
    # Using a simplified vectorized approach or numba if possible, but pandas iter is slow.
    # For now, we'll implement a fast numpy-based Supertrend.
    st, direction = _supertrend(high, low, close, 10, 3.0)
    df['supertrend'] = st
    df['supertrend_dir'] = direction

    return df

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def _rsi(series: pd.Series, period: int) -> pd.Series:
    """
    RSI using Wilder's Smoothing (ewm with alpha=1/period).
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    alpha = 1.0 / period
    avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    """
    ATR using Wilder's Smoothing.
    """
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Wilder's smoothing for ATR
    return tr.ewm(alpha=1.0/period, adjust=False).mean()

def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    """
    ADX using Wilder's Smoothing.
    """
    up_move = high - high.shift()
    down_move = low.shift() - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    plus_dm = pd.Series(plus_dm, index=high.index)
    minus_dm = pd.Series(minus_dm, index=high.index)

    tr_smooth = _atr(high, low, close, period)

    alpha = 1.0 / period
    plus_di = 100 * plus_dm.ewm(alpha=alpha, adjust=False).mean() / tr_smooth
    minus_di = 100 * minus_dm.ewm(alpha=alpha, adjust=False).mean() / tr_smooth

    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    return dx.ewm(alpha=alpha, adjust=False).mean()

def _bollinger_bands(series: pd.Series, period: int, std_dev: float):
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return upper, middle, lower

def _supertrend(high: pd.Series, low: pd.Series, close: pd.Series, period: int, multiplier: float):
    # Calculate ATR
    atr = _atr(high, low, close, period)

    hl2 = (high + low) / 2
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)

    # Initialize arrays
    n = len(close)
    final_upper = np.zeros(n)
    final_lower = np.zeros(n)
    supertrend = np.zeros(n)
    direction = np.zeros(n) # 1: up, -1: down

    # Convert to numpy for speed
    c = close.values
    bu = basic_upper.values
    bl = basic_lower.values

    # Iterative calculation (numba would be better but keeping deps minimal)
    # Just standard python loop over numpy arrays is reasonably fast for daily data

    # Init first values
    final_upper[0] = bu[0]
    final_lower[0] = bl[0]

    for i in range(1, n):
        # Final Upper
        if (bu[i] < final_upper[i-1]) or (c[i-1] > final_upper[i-1]):
            final_upper[i] = bu[i]
        else:
            final_upper[i] = final_upper[i-1]

        # Final Lower
        if (bl[i] > final_lower[i-1]) or (c[i-1] < final_lower[i-1]):
            final_lower[i] = bl[i]
        else:
            final_lower[i] = final_lower[i-1]

        # Direction
        if i == 0:
            direction[i] = 1
        else:
            if direction[i-1] == 1:
                if c[i] < final_lower[i]:
                    direction[i] = -1
                else:
                    direction[i] = 1
            else:
                if c[i] > final_upper[i]:
                    direction[i] = 1
                else:
                    direction[i] = -1

        # Supertrend value
        if direction[i] == 1:
            supertrend[i] = final_lower[i]
        else:
            supertrend[i] = final_upper[i]

    return pd.Series(supertrend, index=close.index), pd.Series(direction, index=close.index)
