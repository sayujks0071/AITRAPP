"""Strategy Grammar and Logic"""
import pandas as pd
import numpy as np
from typing import Dict, Any
from packages.strategy_foundry.adapters.core_indicators import CoreIndicatorAdapter

class StrategyGrammar:
    def __init__(self, spec: Dict[str, Any]):
        self.spec = spec
        self.params = spec.get("params", {})
        self.adapter = CoreIndicatorAdapter()

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate signals: 1 (Long), -1 (Short), 0 (Neutral).
        """
        logic_type = self.spec.get("logic_type")

        if logic_type == "trend_crossover":
            return self._trend_crossover(df)
        elif logic_type == "rsi_mean_reversion":
            return self._rsi_mean_reversion(df)
        elif logic_type == "supertrend_follow":
            return self._supertrend_follow(df)
        elif logic_type == "donchian_breakout":
            return self._donchian_breakout(df)
        elif logic_type == "bollinger_mean_reversion":
            return self._bollinger_mean_reversion(df)
        else:
            return pd.Series(0, index=df.index)

    def _trend_crossover(self, df: pd.DataFrame) -> pd.Series:
        fast = self.adapter.ema(df["Close"], self.params["ma_fast"])
        slow = self.adapter.ema(df["Close"], self.params["ma_slow"])

        # 1 where fast > slow, -1 where fast < slow
        signals = np.where(fast > slow, 1, -1)
        return pd.Series(signals, index=df.index)

    def _rsi_mean_reversion(self, df: pd.DataFrame) -> pd.Series:
        rsi = self.adapter.rsi(df["Close"], self.params["rsi_period"])

        # Long if RSI < Oversold, Short if RSI > Overbought
        signals = pd.Series(0, index=df.index)
        signals[rsi < self.params["rsi_oversold"]] = 1
        signals[rsi > self.params["rsi_overbought"]] = -1

        # Hold signals? Simple reversal logic:
        # If we just want raw states, this is fine.
        # For a stateful system, we might latch.
        # MVP: Raw state signals, backtest engine handles latching/position management.
        return signals

    def _supertrend_follow(self, df: pd.DataFrame) -> pd.Series:
        # Supertrend returns the trend line, we need direction
        # Core adapter returns the line value. We need to infer direction or implement direction logic.
        # Let's reimplement direction logic quickly since adapter exposes just the calculation helpers usually.
        # Actually my adapter implementation returns just the line.
        # I need to know if Close > Supertrend (Long) or Close < Supertrend (Short).

        st_line = self.adapter.supertrend(
            df["High"], df["Low"], df["Close"],
            self.params["st_period"], self.params["st_multiplier"]
        )

        signals = np.where(df["Close"] > st_line, 1, -1)
        return pd.Series(signals, index=df.index)

    def _donchian_breakout(self, df: pd.DataFrame) -> pd.Series:
        upper = df["High"].rolling(window=self.params["donchian_period"]).max().shift(1)
        lower = df["Low"].rolling(window=self.params["donchian_period"]).min().shift(1)

        signals = pd.Series(0, index=df.index)
        signals[df["Close"] > upper] = 1
        signals[df["Close"] < lower] = -1

        # Forward fill 0s to maintain position?
        # A breakout strategy usually holds until reverse signal.
        # We will use ffill in backtest or here.
        # Let's do ffill here to represent "Trend Following" state.
        signals = signals.replace(0, np.nan).ffill().fillna(0)
        return signals

    def _bollinger_mean_reversion(self, df: pd.DataFrame) -> pd.Series:
        upper, middle, lower = self.adapter.bollinger_bands(
            df["Close"], self.params["bb_period"], self.params["bb_std"]
        )

        signals = pd.Series(0, index=df.index)
        # Long if close < lower
        signals[df["Close"] < lower] = 1
        # Short if close > upper
        signals[df["Close"] > upper] = -1
        # Exit/Neutral if crosses middle?
        # Simple MR: Hold until opposite band or middle.
        # MVP: Close at middle.

        # 0 means close/neutral.
        # Logic:
        # If Long and > middle -> 0
        # If Short and < middle -> 0

        # This requires state loop.
        # Let's keep it simple: Raw signals.
        return signals
