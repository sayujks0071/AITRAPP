"""Parameter definitions for strategy generation"""
import random
from typing import Any, List, Dict, Union

class Parameter:
    def __init__(self, name: str):
        self.name = name

    def sample(self) -> Any:
        raise NotImplementedError

class IntParam(Parameter):
    def __init__(self, name: str, min_val: int, max_val: int, step: int = 1):
        super().__init__(name)
        self.min_val = min_val
        self.max_val = max_val
        self.step = step

    def sample(self) -> int:
        return random.randrange(self.min_val, self.max_val + 1, self.step)

class FloatParam(Parameter):
    def __init__(self, name: str, min_val: float, max_val: float, step: float = 0.1):
        super().__init__(name)
        self.min_val = min_val
        self.max_val = max_val
        self.step = step

    def sample(self) -> float:
        # Approximate float range
        steps = int((self.max_val - self.min_val) / self.step)
        return round(self.min_val + random.randint(0, steps) * self.step, 2)

class ChoiceParam(Parameter):
    def __init__(self, name: str, choices: List[Any]):
        super().__init__(name)
        self.choices = choices

    def sample(self) -> Any:
        return random.choice(self.choices)

# --- Block Definitions ---

ENTRY_BLOCKS = {
    "DonchianBreakout": [
        IntParam("period", 10, 60, 5),
    ],
    "ORB": [
        IntParam("minutes", 15, 60, 15), # 15, 30, 45, 60
    ],
    "EMACross": [
        IntParam("fast_period", 5, 20, 1),
        IntParam("slow_period", 20, 100, 5),
    ],
    "RSIReversion": [
        IntParam("period", 7, 21, 2),
        IntParam("lower_threshold", 20, 40, 5),
        IntParam("upper_threshold", 60, 80, 5),
    ],
    "BollingerReversion": [
        IntParam("period", 10, 30, 2),
        FloatParam("std", 1.5, 2.5, 0.1),
    ]
}

EXIT_BLOCKS = {
    "ATRStop": [
        FloatParam("multiplier", 1.0, 4.0, 0.5),
        IntParam("period", 10, 20, 2),
    ],
    "TimeStop": [
        IntParam("max_bars", 6, 40, 2), # e.g. on 15m, 12 bars = 3 hours
    ],
    "ProfitTarget": [
        FloatParam("risk_reward", 1.0, 4.0, 0.5), # relative to ATR stop usually, or just fixed %?
                                                  # Let's assume this block implies an RR target relative to ATR if ATRStop exists.
                                                  # But for simplicity, let's make it ATR based target.
        FloatParam("atr_multiplier", 2.0, 8.0, 1.0),
    ],
    "EODExit": [
        # No params, hardcoded time usually
    ]
}

FILTER_BLOCKS = {
    "TrendFilterEMA": [
        IntParam("period", 50, 200, 25), # High timeframe trend check often implied
    ],
    "VolatilityFilter": [
        IntParam("atr_period", 10, 20, 2),
        IntParam("percentile", 20, 80, 10), # e.g. only trade if ATR > 20th percentile
    ]
}
