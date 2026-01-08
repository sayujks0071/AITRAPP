"""
Strategy Logic Interpreter.
Converts StrategyCandidate blocks into executable logic.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.adapters import core_indicators as ind

class StrategyInterpreter:
    def __init__(self, candidate: StrategyCandidate):
        self.candidate = candidate

    def generate_positions(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate target positions (-1, 0, 1) for the dataframe.
        """
        # Default: Neutral
        signals = pd.Series(0, index=df.index)

        # 1. Calculate base signals from Core Logic
        # We need to parse blocks
        core_block = next((b for b in self.candidate.blocks if b["type"] in
                           ["EMA_CROSS", "SMA_CROSS", "SUPERTREND", "DONCHIAN_BREAKOUT", "RSI_REVERSION", "BB_MEAN_REVERSION"]), None)

        if not core_block:
            return signals # Should not happen if grammar is correct

        base_signal = self._evaluate_core(df, core_block)

        # 2. Apply Filters
        mask = pd.Series(True, index=df.index)
        for block in self.candidate.blocks:
            if block["type"] in ["RSI_FILTER", "ADX_FILTER"]:
                mask = mask & self._evaluate_filter(df, block)

        # Apply mask: if filter is False, signal is 0 (or previous? stick to 0 for simplicity or no entry)
        # Actually, filters usually prevent *entries*.
        # For simplicity in this vectorized engine: Filter zeros out signals.
        final_signal = base_signal * mask.astype(int)

        # 3. Apply Risk (Stops)
        # This is harder to vectorize perfectly because it depends on entry price.
        # However, we can approximate or handle it in the backtest engine loop.
        # But the requirement says "generate_positions(df) -> positions".
        # If the strategy has "ATR_STOP", it implies an exit rule.
        # The backtest engine is responsible for exits based on risk rules if they are stateful (like trailing stop).
        # "apply_risk_overlay" was mentioned in requirements.

        # For now, generate the raw signal (-1, 1, 0)
        # The backtest engine will handle the stop loss execution.

        return final_signal

    def _evaluate_core(self, df: pd.DataFrame, block: Dict[str, Any]) -> pd.Series:
        btype = block["type"]
        p = block["params"]

        signal = pd.Series(0, index=df.index)

        if btype == "EMA_CROSS":
            fast = ind.ema(df["close"], p["fast"])
            slow = ind.ema(df["close"], p["slow"])
            # 1 where fast > slow, -1 where fast < slow
            signal = np.where(fast > slow, 1, -1)

        elif btype == "SMA_CROSS":
            fast = ind.sma(df["close"], p["fast"])
            slow = ind.sma(df["close"], p["slow"])
            signal = np.where(fast > slow, 1, -1)

        elif btype == "SUPERTREND":
            st_val, direction = ind.supertrend(df, p["period"], p["multiplier"])
            signal = direction # 1 or -1

        elif btype == "DONCHIAN_BREAKOUT":
            upper, lower = ind.donchian_channel(df, p["period"])
            # Breakout: close > upper.shift -> Buy. close < lower.shift -> Sell.
            # Hold otherwise.
            # Vectorized:
            buy = df["close"] > upper.shift(1)
            sell = df["close"] < lower.shift(1)

            # Forward fill signals
            # 1 for Buy, -1 for Sell, NaN for hold
            raw = pd.Series(np.nan, index=df.index)
            raw[buy] = 1
            raw[sell] = -1
            signal = raw.ffill().fillna(0)

        elif btype == "RSI_REVERSION":
            r = ind.rsi(df["close"], p["period"])
            # Mean reversion: RSI < lower -> Buy (Oversold)
            # RSI > upper -> Sell (Overbought)
            # Else flat? Or hold? Usually revert strategies exit at mean (50).
            # Let's say: Buy if < lower, Sell if > upper.
            buy = r < p["lower"]
            sell = r > p["upper"]

            raw = pd.Series(0, index=df.index)
            raw[buy] = 1
            raw[sell] = -1
            # If 0, we exit? Or hold?
            # Reversion strategies often hold until opposite signal or stop.
            # Let's ffill for now to hold the position.
            # But wait, if RSI is between, we might want to exit?
            # Simpler: ffill.
            raw = raw.replace(0, np.nan)
            signal = raw.ffill().fillna(0)

        elif btype == "BB_MEAN_REVERSION":
            upper, mid, lower = ind.bollinger_bands(df["close"], p["period"], p["std"])
            # Buy at lower, Sell at upper
            buy = df["close"] < lower
            sell = df["close"] > upper

            raw = pd.Series(np.nan, index=df.index)
            raw[buy] = 1
            raw[sell] = -1
            signal = raw.ffill().fillna(0)

        return pd.Series(signal, index=df.index)

    def _evaluate_filter(self, df: pd.DataFrame, block: Dict[str, Any]) -> pd.Series:
        btype = block["type"]
        p = block["params"]

        if btype == "RSI_FILTER":
            r = ind.rsi(df["close"], p["period"])
            return (r >= p["min"]) & (r <= p["max"])

        elif btype == "ADX_FILTER":
            a = ind.adx(df, p["period"])
            return a >= p["min_strength"]

        return pd.Series(True, index=df.index)

    def get_risk_params(self) -> Dict[str, Any]:
        """Extract risk parameters for the engine."""
        risk_block = next((b for b in self.candidate.blocks if b["type"] in ["ATR_STOP", "TRAILING_STOP"]), None)
        if risk_block:
            return {"type": risk_block["type"], "params": risk_block["params"]}
        return {}
