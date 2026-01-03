import pandas as pd
import numpy as np

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add technical indicators to the dataframe.
    """
    if df.empty:
        return df

    df = df.copy()
    close = df['close']
    high = df['high']
    low = df['low']

    # EMAs
    df['ema_10'] = close.ewm(span=10, adjust=False).mean()
    df['ema_20'] = close.ewm(span=20, adjust=False).mean()
    df['ema_50'] = close.ewm(span=50, adjust=False).mean()
    df['ema_200'] = close.ewm(span=200, adjust=False).mean()

    # RSI 14
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df['rsi_14'] = 100 - (100 / (1 + rs))

    # ATR 14
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr_14'] = tr.rolling(window=14).mean()

    # Bollinger Bands (20, 2)
    bb_mean = close.rolling(window=20).mean()
    bb_std = close.rolling(window=20).std()
    df['bb_upper'] = bb_mean + (bb_std * 2)
    df['bb_lower'] = bb_mean - (bb_std * 2)

    # Donchian (20)
    df['donchian_upper_20'] = high.rolling(window=20).max()
    df['donchian_lower_20'] = low.rolling(window=20).min()

    # ADX 14
    up_move = high - high.shift()
    down_move = low.shift() - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / df['atr_14']
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / df['atr_14']
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df['adx_14'] = dx.ewm(alpha=1/14, adjust=False).mean()

    return df
