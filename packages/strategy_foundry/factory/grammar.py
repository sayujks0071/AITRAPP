import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
import hashlib
import json
from packages.strategy_foundry.adapters.core_indicators import VectorizedIndicatorCalculator

class StrategyBlock:
    def __init__(self, name: str, params: Dict[str, Any]):
        self.name = name
        self.params = params

    def compute_signal(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.Series:
        raise NotImplementedError

    def __repr__(self):
        return f"{self.name}({self.params})"

    def to_dict(self):
        return {"type": self.name, "params": self.params}

class EmaCrossBlock(StrategyBlock):
    def __init__(self, fast_period: int, slow_period: int):
        super().__init__("EmaCross", {"fast": fast_period, "slow": slow_period})

    def compute_signal(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.Series:
        # Pre-calculated in indicators dict or calculated here?
        # Better to calculate here or use cache.
        # We will assume 'indicators' has raw data or calculator
        calc = VectorizedIndicatorCalculator()
        close = df["close"]
        ema_fast = calc.ema(close, self.params["fast"])
        ema_slow = calc.ema(close, self.params["slow"])

        # Signal: 1 if Fast > Slow (uptrend), -1 if Fast < Slow
        # We want to catch the crossover.
        # For trend following: hold 1 while Fast > Slow.
        signal = pd.Series(0, index=df.index)
        signal[ema_fast > ema_slow] = 1
        signal[ema_fast < ema_slow] = -1
        return signal

class RsiFilterBlock(StrategyBlock):
    def __init__(self, period: int, threshold: float, mode: str):
        # mode: "long_if_above" (trend), "long_if_below" (mean rev)
        super().__init__("RsiFilter", {"period": period, "threshold": threshold, "mode": mode})

    def compute_signal(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.Series:
        calc = VectorizedIndicatorCalculator()
        rsi = calc.rsi(df["close"].values, self.params["period"])
        rsi_s = pd.Series(rsi, index=df.index)

        signal = pd.Series(0, index=df.index)
        if self.params["mode"] == "long_if_above":
            signal[rsi_s > self.params["threshold"]] = 1
        elif self.params["mode"] == "long_if_below":
            signal[rsi_s < self.params["threshold"]] = 1

        return signal

class SupertrendBlock(StrategyBlock):
    def __init__(self, period: int, multiplier: float):
        super().__init__("Supertrend", {"period": period, "multiplier": multiplier})

    def compute_signal(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.Series:
        calc = VectorizedIndicatorCalculator()
        st, direction = calc.supertrend(
            df["high"].values, df["low"].values, df["close"].values,
            self.params["period"], self.params["multiplier"]
        )
        # direction is 1 (up) or -1 (down)
        return pd.Series(direction, index=df.index)

class DonchianBlock(StrategyBlock):
    def __init__(self, period: int):
        super().__init__("Donchian", {"period": period})

    def compute_signal(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.Series:
        calc = VectorizedIndicatorCalculator()
        upper, lower = calc.donchian(df["high"], df["low"], self.params["period"])
        close = df["close"]

        signal = pd.Series(0, index=df.index)
        signal[close > upper.shift(1)] = 1  # Breakout up
        signal[close < lower.shift(1)] = -1 # Breakout down

        # Propagate signal? Donchian is usually breakout entry.
        # For simplicty, this block returns "State" 1 if price > prev_upper
        # Real Donchian strategy holds until touches lower.
        # Here we return instantaneous state.
        return signal

class Strategy:
    def __init__(self, blocks: List[StrategyBlock], stop_loss_atr: float, take_profit_atr: float):
        self.blocks = blocks
        self.stop_loss_atr = stop_loss_atr
        self.take_profit_atr = take_profit_atr
        self.id = self._generate_id()

    def _generate_id(self):
        desc = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.md5(desc.encode()).hexdigest()[:12]

    def to_dict(self):
        return {
            "blocks": [b.to_dict() for b in self.blocks],
            "risk": {
                "stop_loss_atr": self.stop_loss_atr,
                "take_profit_atr": self.take_profit_atr
            }
        }

    @property
    def rule_summary(self) -> str:
        rules = " AND ".join([repr(b) for b in self.blocks])
        return f"Signal({rules}) | Risk(SL={self.stop_loss_atr}ATR, TP={self.take_profit_atr}ATR)"

    def generate_positions(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate target positions (-1, 0, 1).
        Logic: All blocks must agree on direction (or be 0).
        For Long Only: All blocks must be >= 0, and at least one is 1.
        """
        if df.empty: return pd.Series()

        combined_signal = pd.Series(0, index=df.index)

        # We need to accumulate consensus.
        # Simple logic: Voting.
        # Or Strict: All must be 1 to go Long.

        # Let's go with "Intersection" (AND) for entry.
        # If any block says -1, we don't go long.
        # If all blocks >= 0 and sum > 0 -> Long.

        signals = []
        for block in self.blocks:
            signals.append(block.compute_signal(df, {}))

        if not signals:
            return combined_signal

        # Stack signals
        sig_df = pd.concat(signals, axis=1)

        # Long Logic
        # All signals must be >= 0 (no explicit sell signals)
        # At least one signal must be 1 (explicit buy signal)
        long_condition = (sig_df >= 0).all(axis=1) & (sig_df.sum(axis=1) >= 1)

        # Short Logic (Optional, disabled by default in foundry usually, but here we support signals)
        short_condition = (sig_df <= 0).all(axis=1) & (sig_df.sum(axis=1) <= -1)

        combined_signal[long_condition] = 1
        combined_signal[short_condition] = -1

        return combined_signal

    def get_atr_array(self, df: pd.DataFrame):
        calc = VectorizedIndicatorCalculator()
        return calc.atr(df["high"].values, df["low"].values, df["close"].values, period=14)
