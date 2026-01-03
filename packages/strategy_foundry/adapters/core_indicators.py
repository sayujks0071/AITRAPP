import pandas as pd
import numpy as np
import structlog

logger = structlog.get_logger(__name__)

class VectorizedIndicators:
    """
    Computes technical indicators on full DataFrames (vectorized).
    Adapts logic from packages/core/indicators.py where possible.
    """

    @staticmethod
    def add_all(df: pd.DataFrame) -> pd.DataFrame:
        """Add all available indicators to the dataframe"""
        df = df.copy()

        # EMA
        df["ema_10"] = VectorizedIndicators.ema(df["close"], 10)
        df["ema_20"] = VectorizedIndicators.ema(df["close"], 20)
        df["ema_50"] = VectorizedIndicators.ema(df["close"], 50)
        df["ema_200"] = VectorizedIndicators.ema(df["close"], 200)

        # SMA
        df["sma_20"] = df["close"].rolling(window=20).mean()

        # RSI
        df["rsi_14"] = VectorizedIndicators.rsi(df["close"], 14)

        # ATR
        df["atr_14"] = VectorizedIndicators.atr(df, 14)

        # Bollinger Bands
        upper, mid, lower = VectorizedIndicators.bollinger_bands(df["close"], 20, 2.0)
        df["bb_upper"] = upper
        df["bb_lower"] = lower
        df["bb_width"] = (upper - lower) / mid

        # Donchian
        upper, lower = VectorizedIndicators.donchian(df, 20)
        df["dc_upper"] = upper
        df["dc_lower"] = lower

        # ADX
        df["adx_14"] = VectorizedIndicators.adx(df, 14)

        # Supertrend
        st, direction = VectorizedIndicators.supertrend(df, 10, 3.0)
        df["supertrend"] = st
        df["supertrend_dir"] = direction

        return df

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()

        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        # Wilder's Smoothing
        return tr.ewm(alpha=1/period, adjust=False).mean()

    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0):
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower

    @staticmethod
    def donchian(df: pd.DataFrame, period: int = 20):
        upper = df["high"].rolling(window=period).max()
        lower = df["low"].rolling(window=period).min()
        return upper, lower

    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
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

        # Wilder's Smoothing for ATR and DMs
        atr = tr.ewm(alpha=1/period, adjust=False).mean()

        plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean() / atr
        minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1/period, adjust=False).mean() / atr

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        # ADX is smoothed DX
        return dx.ewm(alpha=1/period, adjust=False).mean()

    @staticmethod
    def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
        """
        Supertrend indicator.
        This uses an iterative approach as it's recursive.
        """
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        # Calculate ATR
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        tr2[0] = tr1[0]
        tr3[0] = tr1[0]
        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        atr_series = pd.Series(tr).rolling(window=period).mean()
        atr = atr_series.fillna(0).values

        hl_avg = (high + low) / 2
        basic_ub = hl_avg + (multiplier * atr)
        basic_lb = hl_avg - (multiplier * atr)

        n = len(df)
        final_ub = np.zeros(n)
        final_lb = np.zeros(n)
        supertrend = np.zeros(n)
        direction = np.zeros(n, dtype=int)

        # Initialize
        final_ub[0] = basic_ub[0]
        final_lb[0] = basic_lb[0]

        for i in range(1, n):
            # Final Upper Band
            if basic_ub[i] < final_ub[i-1] or close[i-1] > final_ub[i-1]:
                final_ub[i] = basic_ub[i]
            else:
                final_ub[i] = final_ub[i-1]

            # Final Lower Band
            if basic_lb[i] > final_lb[i-1] or close[i-1] < final_lb[i-1]:
                final_lb[i] = basic_lb[i]
            else:
                final_lb[i] = final_lb[i-1]

            # Supertrend
            if supertrend[i-1] == final_ub[i-1] and close[i] <= final_ub[i]:
                supertrend[i] = final_ub[i]
                direction[i] = -1
            elif supertrend[i-1] == final_ub[i-1] and close[i] > final_ub[i]:
                supertrend[i] = final_lb[i]
                direction[i] = 1
            elif supertrend[i-1] == final_lb[i-1] and close[i] >= final_lb[i]:
                supertrend[i] = final_lb[i]
                direction[i] = 1
            elif supertrend[i-1] == final_lb[i-1] and close[i] < final_lb[i]:
                supertrend[i] = final_ub[i]
                direction[i] = -1
            else:
                # Fallback / initialization
                if close[i] <= final_ub[i]:
                    supertrend[i] = final_ub[i]
                    direction[i] = -1
                else:
                    supertrend[i] = final_lb[i]
                    direction[i] = 1

        return pd.Series(supertrend, index=df.index), pd.Series(direction, index=df.index)
