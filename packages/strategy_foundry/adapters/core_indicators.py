"""
Adapter for core indicators.
"""
import pandas as pd
from packages.core.indicators import IndicatorCalculator

class Indicators:
    def __init__(self):
        self.calc = IndicatorCalculator()

    def add_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add all indicators to the DataFrame.
        This modifies the DataFrame in place AND returns it.

        The core IndicatorCalculator calculates *latest* values mostly,
        but for backtesting we need Series.

        Wait, packages.core.indicators mostly returns scalar float or single array for optimization.
        We need full series for vector backtesting.

        We will implement vectorized versions here or reuse internal logic if possible.
        The core calculator DOES compute series internally (e.g. rolling means), but returns iloc[-1].

        We should subclass or just re-implement vector-friendly wrappers.
        """
        # Common indicators needed:
        # ATR, RSI, EMAs, Bollinger, Donchian, Supertrend

        df = df.copy()

        # EMA
        df["ema_9"] = df["Close"].ewm(span=9, adjust=False).mean()
        df["ema_20"] = df["Close"].ewm(span=20, adjust=False).mean()
        df["ema_50"] = df["Close"].ewm(span=50, adjust=False).mean()
        df["ema_200"] = df["Close"].ewm(span=200, adjust=False).mean()

        # RSI
        delta = df["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["rsi_14"] = 100 - (100 / (1 + rs))

        # ATR
        high = df["High"]
        low = df["Low"]
        close = df["Close"]
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df["atr_14"] = tr.rolling(window=14).mean()

        # Bollinger
        sma = df["Close"].rolling(window=20).mean()
        std = df["Close"].rolling(window=20).std()
        df["bb_upper"] = sma + (std * 2)
        df["bb_lower"] = sma - (std * 2)

        # Donchian (20)
        df["donchian_upper"] = df["High"].rolling(window=20).max()
        df["donchian_lower"] = df["Low"].rolling(window=20).min()

        # Supertrend (Basic vector impl)
        # This is hard to vectorize fully due to recursive dependency.
        # For foundry speed, we might approximate or use Numba if available,
        # but let's stick to a loop or just skip supertrend for now if it's too slow.
        # Actually, let's use the core loop but apply it to the whole DF.
        # The core _supertrend method returns an array! Perfect.

        # We need to adapt column names (core expects lowercase)
        df_core = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        st_val, st_dir = self.calc._supertrend(df_core)

        if st_val is not None:
             df["supertrend"] = st_val
             df["supertrend_dir"] = st_dir

        # ADX
        # Core _adx returns float, need series.
        # Re-implementing vector ADX here.
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0

        tr_smooth = tr.rolling(window=14).mean() # Simple rolling for backtest speed vs Wilder
        plus_di = 100 * (plus_dm.rolling(window=14).mean() / tr_smooth)
        minus_di = 100 * (minus_dm.abs().rolling(window=14).mean() / tr_smooth)
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        df["adx_14"] = dx.rolling(window=14).mean()

        return df
