from abc import ABC, abstractmethod
from typing import Dict, Any, List
import pandas as pd
import hashlib
import json

class Strategy(ABC):
    def __init__(self, params: Dict[str, Any]):
        self.params = params
        self.rule_summary = "Base Strategy"

    @abstractmethod
    def generate_positions(self, df: pd.DataFrame) -> pd.Series:
        """Return series of -1, 0, 1"""
        pass

    @abstractmethod
    def apply_risk_overlay(self, df: pd.DataFrame, positions: pd.Series) -> pd.Series:
        """Apply stops/targets"""
        pass

    def get_id(self) -> str:
        """Stable hash of params"""
        s = json.dumps(self.params, sort_keys=True)
        return hashlib.sha256(s.encode()).hexdigest()[:12]

    def __repr__(self):
        return f"Strategy({self.rule_summary})"

class SimpleTrendStrategy(Strategy):
    """
    EMA Crossover + RSI Filter
    """
    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.fast_period = params.get('ema_fast', 10)
        self.slow_period = params.get('ema_slow', 50)
        self.rsi_period = params.get('rsi_period', 14)
        self.rsi_min = params.get('rsi_min', 40)
        self.rsi_max = params.get('rsi_max', 60)
        self.rule_summary = f"EMA Cross({self.fast_period}/{self.slow_period}) + RSI({self.rsi_period}) in [{self.rsi_min}, {self.rsi_max}]"

    def generate_positions(self, df: pd.DataFrame) -> pd.Series:
        ema_fast = df[f"ema_{self.fast_period}"] if f"ema_{self.fast_period}" in df else df['close'].ewm(span=self.fast_period).mean()
        ema_slow = df[f"ema_{self.slow_period}"] if f"ema_{self.slow_period}" in df else df['close'].ewm(span=self.slow_period).mean()
        rsi = df['rsi'] if 'rsi' in df else pd.Series(50, index=df.index)

        long_cond = (ema_fast > ema_slow) & (rsi > self.rsi_min)
        short_cond = (ema_fast < ema_slow) & (rsi < self.rsi_max)

        positions = pd.Series(0, index=df.index)
        positions[long_cond] = 1
        positions[short_cond] = -1 # Assuming short enabled, if not engine will filter

        return positions

    def apply_risk_overlay(self, df: pd.DataFrame, positions: pd.Series) -> pd.Series:
        # Simple stop logic could be applied here, but for now we trust the signal
        # Engine handles ATR stops usually.
        # But if we want time-based exits or specific logic:
        return positions

class MeanReversionStrategy(Strategy):
    """
    Bollinger Band + RSI Reversion
    """
    def __init__(self, params):
        super().__init__(params)
        self.rsi_lower = params.get('rsi_lower', 30)
        self.rsi_upper = params.get('rsi_upper', 70)
        self.rule_summary = f"BB Reversion + RSI < {self.rsi_lower} / > {self.rsi_upper}"

    def generate_positions(self, df: pd.DataFrame) -> pd.Series:
        close = df['close']
        bb_lower = df['bb_lower']
        bb_upper = df['bb_upper']
        rsi = df['rsi']

        long_cond = (close < bb_lower) & (rsi < self.rsi_lower)
        short_cond = (close > bb_upper) & (rsi > self.rsi_upper)

        positions = pd.Series(0, index=df.index)
        positions[long_cond] = 1
        positions[short_cond] = -1
        return positions

    def apply_risk_overlay(self, df, positions):
        return positions
