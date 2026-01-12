from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime

def calculate_indicators(df: pd.DataFrame, params: Dict[str, Any] = None) -> pd.DataFrame:
    """
    Adapter to calculate vectorized indicators for the Strategy Foundry.
    Returns a DataFrame with indicator columns added, suitable for vectorized backtesting.
    """
    if params is None:
        params = {}

    # Defaults
    atr_period = params.get('atr_period', 14)
    rsi_period = params.get('rsi_period', 14)
    adx_period = params.get('adx_period', 14)

    df = df.copy()
    close = df['close']
    high = df['high']
    low = df['low']

    # EMA
    df['ema_50'] = close.ewm(span=50, adjust=False).mean()
    df['ema_200'] = close.ewm(span=200, adjust=False).mean()
    df['sma_50'] = close.rolling(window=50).mean()

    # RSI
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/rsi_period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/rsi_period, adjust=False).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # ATR
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = tr.ewm(alpha=1/atr_period, adjust=False).mean()

    # ADX
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm_s = pd.Series(np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0.0), index=df.index)
    minus_dm_s = pd.Series(np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0.0), index=df.index)

    tr_s = tr.ewm(alpha=1/adx_period, adjust=False).mean()
    plus_di = 100 * plus_dm_s.ewm(alpha=1/adx_period, adjust=False).mean() / tr_s
    minus_di = 100 * minus_dm_s.ewm(alpha=1/adx_period, adjust=False).mean() / tr_s
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df['adx'] = dx.ewm(alpha=1/adx_period, adjust=False).mean()

    # Bollinger
    bb_period = params.get('bb_period', 20)
    bb_std = params.get('bb_std', 2.0)
    ma = close.rolling(window=bb_period).mean()
    std = close.rolling(window=bb_period).std()
    df['bb_upper'] = ma + (std * bb_std)
    df['bb_lower'] = ma - (std * bb_std)

    # Supertrend
    st_period = params.get('st_period', 10)
    st_multiplier = params.get('st_multiplier', 3.0)

    # Need ATR for Supertrend Period
    tr_st = tr.ewm(alpha=1/st_period, adjust=False).mean()

    hl_avg = (high + low) / 2
    basic_ub = hl_avg + (st_multiplier * tr_st)
    basic_lb = hl_avg - (st_multiplier * tr_st)

    # Iterative calculation for Supertrend
    n = len(df)
    final_ub = np.zeros(n)
    final_lb = np.zeros(n)
    supertrend = np.zeros(n)
    close_vals = close.values

    # Initialize
    final_ub[0] = basic_ub.iloc[0]
    final_lb[0] = basic_lb.iloc[0]

    for i in range(1, n):
        # Final Upper Band
        if basic_ub.iloc[i] < final_ub[i-1] or close_vals[i-1] > final_ub[i-1]:
            final_ub[i] = basic_ub.iloc[i]
        else:
            final_ub[i] = final_ub[i-1]

        # Final Lower Band
        if basic_lb.iloc[i] > final_lb[i-1] or close_vals[i-1] < final_lb[i-1]:
            final_lb[i] = basic_lb.iloc[i]
        else:
            final_lb[i] = final_lb[i-1]

        # Supertrend
        if supertrend[i-1] == final_ub[i-1]: # Downtrend previously
             if close_vals[i] <= final_ub[i]:
                 supertrend[i] = final_ub[i]
             else:
                 supertrend[i] = final_lb[i]
        else: # Uptrend previously
             if close_vals[i] >= final_lb[i]:
                 supertrend[i] = final_lb[i]
             else:
                 supertrend[i] = final_ub[i]

    df['supertrend'] = supertrend

    return df
