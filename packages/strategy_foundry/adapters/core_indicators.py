"""
Core Indicators Adapter
Implements vectorized versions of technical indicators for backtesting.
Reuses packages/core/indicators where applicable, but optimized for Series operations.
"""
import numpy as np
import pandas as pd
from packages.core.indicators import IndicatorCalculator

class VectorizedIndicators:
    """Vectorized indicator calculations for entire DataFrames"""

    @staticmethod
    def add_all(df: pd.DataFrame) -> pd.DataFrame:
        """Add all supported indicators to the dataframe"""
        # Ensure we have required columns
        required = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required):
            return df

        df = df.copy()

        # Trend
        df['ema_20'] = VectorizedIndicators.ema(df['close'], 20)
        df['ema_50'] = VectorizedIndicators.ema(df['close'], 50)
        df['ema_200'] = VectorizedIndicators.ema(df['close'], 200)
        df['sma_20'] = df['close'].rolling(window=20).mean()

        # Volatility
        df['atr_14'] = VectorizedIndicators.atr(df, 14)
        df['bb_upper'], df['bb_mid'], df['bb_lower'] = VectorizedIndicators.bollinger_bands(df['close'])

        # Momentum
        df['rsi_14'] = VectorizedIndicators.rsi(df['close'], 14)
        df['adx_14'] = VectorizedIndicators.adx(df, 14)

        # Channels
        df['donchian_upper'], df['donchian_lower'] = VectorizedIndicators.donchian(df, 20)

        return df

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0))
        loss = (-delta.where(delta < 0, 0))

        # Wilder's Smoothing
        avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        # Wilder's Smoothing for ATR
        return tr.ewm(alpha=1/period, adjust=False).mean()

    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high = df['high']
        low = df['low']
        close = df['close']

        up_move = high - high.shift()
        down_move = low.shift() - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        plus_dm_series = pd.Series(plus_dm, index=df.index)
        minus_dm_series = pd.Series(minus_dm, index=df.index)

        tr = VectorizedIndicators.atr(df, 1) # True Range

        # Smooth
        atr_smooth = tr.ewm(alpha=1/period, adjust=False).mean()
        plus_di = 100 * plus_dm_series.ewm(alpha=1/period, adjust=False).mean() / atr_smooth
        minus_di = 100 * minus_dm_series.ewm(alpha=1/period, adjust=False).mean() / atr_smooth

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        return dx.ewm(alpha=1/period, adjust=False).mean()

    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20, std: float = 2.0):
        mid = series.rolling(window=period).mean()
        sigma = series.rolling(window=period).std()
        upper = mid + (std * sigma)
        lower = mid - (std * sigma)
        return upper, mid, lower

    @staticmethod
    def donchian(df: pd.DataFrame, period: int = 20):
        upper = df['high'].rolling(window=period).max()
        lower = df['low'].rolling(window=period).min()
        return upper, lower
