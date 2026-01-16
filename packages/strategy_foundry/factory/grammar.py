"""Strategy Grammar and Rules"""
import abc
import numpy as np
import pandas as pd
from typing import Dict, Any, List

class Rule(abc.ABC):
    @abc.abstractmethod
    def generate_signal(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.Series:
        """Returns series of -1, 0, 1"""
        pass

    @abc.abstractmethod
    def description(self) -> str:
        pass

class TrendFollowingRule(Rule):
    def __init__(self, fast_period: int, slow_period: int):
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate_signal(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.Series:
        # Assuming indicators calculated outside or calc here
        # For simplicity, we assume indicators dict might contain pre-calc series
        # BUT to be safe and self-contained, we might use the adapter
        # Actually, let's keep it simple: passed indicators dict has raw series from adapter

        # We'll use the df directly with adapter mostly
        # But here we define logic.

        # Check if we have pre-calced EMAs
        key_fast = f"ema_{self.fast_period}"
        key_slow = f"ema_{self.slow_period}"

        fast = indicators.get(key_fast)
        slow = indicators.get(key_slow)

        if fast is None or slow is None:
            # Fallback (should be handled by generator/engine pre-calc)
            fast = df['close'].ewm(span=self.fast_period).mean()
            slow = df['close'].ewm(span=self.slow_period).mean()

        signal = np.where(fast > slow, 1, -1)
        return pd.Series(signal, index=df.index)

    def description(self) -> str:
        return f"EMA Crossover ({self.fast_period}, {self.slow_period})"

class SupertrendRule(Rule):
    def __init__(self, period: int, multiplier: float):
        self.period = period
        self.multiplier = multiplier

    def generate_signal(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.Series:
        key_dir = f"st_dir_{self.period}_{self.multiplier}"
        direction = indicators.get(key_dir)

        if direction is None:
            # Should have been pre-calculated
            # We return 0 if missing to avoid crash, but log warning in real system
            return pd.Series(0, index=df.index)

        return direction # -1 for downtrend (short), 1 for uptrend (long)

    def description(self) -> str:
        return f"Supertrend ({self.period}, {self.multiplier})"

class RSIReversionRule(Rule):
    def __init__(self, period: int, lower: int, upper: int):
        self.period = period
        self.lower = lower
        self.upper = upper

    def generate_signal(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.Series:
        key_rsi = f"rsi_{self.period}"
        rsi = indicators.get(key_rsi)

        if rsi is None: return pd.Series(0, index=df.index)

        signal = pd.Series(0, index=df.index)
        signal[rsi < self.lower] = 1
        signal[rsi > self.upper] = -1

        # This is a stateful rule usually (enter on cross, exit on mean),
        # but for simple grammar we might treat it as "be long if oversold"
        # Better: Signal only on trigger.
        # Let's make it simple state: Long if < Lower, Short if > Upper, else 0 (Hold/Flat?)
        # For a pure signal generator:
        return signal

    def description(self) -> str:
        return f"RSI Reversion ({self.period}: <{self.lower} buy, >{self.upper} sell)"

class StopLossRule(Rule):
    def __init__(self, atr_period: int, multiplier: float):
        self.atr_period = atr_period
        self.multiplier = multiplier

    def generate_signal(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.Series:
        # Stop loss is an exit rule, usually applied ON TOP of entry signals.
        # In this grammar, we might return a "mask" or this might be applied by the engine.
        # For now, let's treat it as a placeholder that the engine uses.
        return pd.Series(0, index=df.index) # Logic is in engine

    def description(self) -> str:
        return f"ATR Stop ({self.atr_period}, {self.multiplier}x)"

