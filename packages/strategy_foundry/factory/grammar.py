"""
Strategy Grammar and Parameter Space.
"""
import random
import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass
class StrategyCandidate:
    id: str
    entry_rules: List[Dict[str, Any]]
    exit_rules: List[Dict[str, Any]]
    params: Dict[str, Any]

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def from_json(cls, json_str: str):
        data = json.loads(json_str)
        return cls(**data)

    def generate_id(self) -> str:
        # Create a stable hash based on rules and params
        content = json.dumps({
            "entry": sorted(str(r) for r in self.entry_rules),
            "exit": sorted(str(r) for r in self.exit_rules),
            "params": dict(sorted(self.params.items()))
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:12]

class ParameterSpace:
    """Defines valid ranges for parameters."""

    RANGES = {
        "rsi_period": [14], # Fixed for simplicity or [7, 14, 21]
        "rsi_buy_threshold": [20, 25, 30, 35, 40],
        "rsi_sell_threshold": [60, 65, 70, 75, 80],

        "ema_fast": [10, 20],
        "ema_slow": [50, 200],

        "bb_period": [20],
        "bb_std": [2.0],

        "atr_period": [14],
        "stop_loss_atr": [1.0, 1.5, 2.0, 3.0],
        "take_profit_atr": [2.0, 3.0, 4.0, 5.0], # or None

        "supertrend_period": [10],
        "supertrend_multiplier": [3],

        "max_bars_hold": [5, 10, 20, 50, 252], # Time stop
    }

    @staticmethod
    def sample(param_name: str):
        return random.choice(ParameterSpace.RANGES.get(param_name, [0]))
