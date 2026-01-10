"""Strategy Grammar and Rules"""
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Dict
import hashlib
import json

@dataclass
class Rule:
    """Base class for a strategy rule/block"""
    name: str
    params: Dict[str, float]

    def to_dict(self):
        return {"name": self.name, "params": self.params}

    @property
    def signature(self):
        """Unique signature for deduplication"""
        # Sort params to ensure deterministic string
        param_str = json.dumps(self.params, sort_keys=True)
        return f"{self.name}:{param_str}"

@dataclass
class StrategyConfig:
    """Definition of a generated strategy"""
    entry_rules: List[Rule]
    exit_rules: List[Rule]
    risk_rules: List[Rule]

    def get_id(self) -> str:
        """Stable ID hash of the strategy configuration"""
        # Compose all signatures
        sigs = [r.signature for r in self.entry_rules + self.exit_rules + self.risk_rules]
        full_str = "|".join(sorted(sigs))
        return hashlib.md5(full_str.encode()).hexdigest()

    def to_json(self):
        return {
            "id": self.get_id(),
            "entry": [r.to_dict() for r in self.entry_rules],
            "exit": [r.to_dict() for r in self.exit_rules],
            "risk": [r.to_dict() for r in self.risk_rules]
        }

    @classmethod
    def from_json(cls, data):
        return cls(
            entry_rules=[Rule(**r) for r in data["entry"]],
            exit_rules=[Rule(**r) for r in data["exit"]],
            risk_rules=[Rule(**r) for r in data["risk"]]
        )

# --- Available Blocks ---

# Trend
class TrendFollowBlock:
    TYPES = ["EMA_CROSS", "SUPERTREND", "DONCHIAN"]

    @staticmethod
    def get_params(type_name):
        if type_name == "EMA_CROSS":
            return {"fast": [5, 10, 20], "slow": [20, 50, 100]}
        elif type_name == "SUPERTREND":
            return {"period": [7, 10, 14], "multiplier": [2.0, 3.0]}
        elif type_name == "DONCHIAN":
            return {"period": [20, 50]}
        return {}

# Mean Reversion
class MeanReversionBlock:
    TYPES = ["RSI_OS_OB", "BB_REVERSION"]

    @staticmethod
    def get_params(type_name):
        if type_name == "RSI_OS_OB":
            return {"period": [14], "lower": [30, 40], "upper": [60, 70]}
        elif type_name == "BB_REVERSION":
            return {"period": [20], "std": [2.0]}
        return {}

# Risk
class RiskBlock:
    TYPES = ["ATR_STOP", "PCT_STOP"]

    @staticmethod
    def get_params(type_name):
        if type_name == "ATR_STOP":
            return {"period": [14], "multiplier": [1.5, 2.0, 3.0]}
        elif type_name == "PCT_STOP":
            return {"pct": [0.01, 0.02, 0.05]}
        return {}
