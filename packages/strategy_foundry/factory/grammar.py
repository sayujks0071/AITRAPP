"""
Strategy Grammar and Generator.
Defines the components and logic to generate random valid strategies.
"""
import random
import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class StrategyCandidate:
    id: str
    blocks: List[Dict[str, Any]]

    def to_json(self) -> str:
        return json.dumps({"id": self.id, "blocks": self.blocks}, sort_keys=True)

    @classmethod
    def from_json(cls, json_str: str):
        data = json.loads(json_str)
        return cls(id=data["id"], blocks=data["blocks"])

    @property
    def rule_summary(self) -> str:
        summaries = []
        for block in self.blocks:
            btype = block["type"]
            params = block["params"]
            p_str = ", ".join([f"{k}={v}" for k,v in params.items()])
            summaries.append(f"{btype}({p_str})")
        return " AND ".join(summaries)

class Grammar:
    """
    Strategy Generation Grammar.
    """

    TREND_BLOCKS = ["EMA_CROSS", "SMA_CROSS", "SUPERTREND", "DONCHIAN_BREAKOUT"]
    MEAN_REV_BLOCKS = ["RSI_REVERSION", "BB_MEAN_REVERSION"]
    VOLATILITY_BLOCKS = ["ATR_STOP", "TRAILING_STOP"]
    FILTERS = ["RSI_FILTER", "ADX_FILTER"]

    @staticmethod
    def random_params(block_type: str) -> Dict[str, Any]:
        if block_type == "EMA_CROSS":
            return {"fast": random.choice([9, 13, 20]), "slow": random.choice([20, 50, 100, 200])}
        elif block_type == "SMA_CROSS":
            return {"fast": random.choice([10, 20, 50]), "slow": random.choice([50, 100, 200])}
        elif block_type == "SUPERTREND":
            return {"period": random.choice([7, 10, 14]), "multiplier": random.choice([2, 3, 4])}
        elif block_type == "DONCHIAN_BREAKOUT":
            return {"period": random.choice([20, 55, 100])}
        elif block_type == "RSI_REVERSION":
            return {"period": 14, "lower": random.choice([20, 30]), "upper": random.choice([70, 80])}
        elif block_type == "BB_MEAN_REVERSION":
            return {"period": 20, "std": 2.0}
        elif block_type == "ATR_STOP":
            return {"period": 14, "multiplier": random.choice([1.5, 2.0, 3.0])}
        elif block_type == "TRAILING_STOP":
            return {"pct": random.choice([1, 2, 3, 5])}
        elif block_type == "RSI_FILTER":
            return {"period": 14, "min": 40, "max": 100}
        elif block_type == "ADX_FILTER":
            return {"period": 14, "min_strength": 20}
        return {}

    @classmethod
    def generate(cls) -> StrategyCandidate:
        """
        Generate a random strategy.
        Composition:
        - 1 Entry/Signal Logic (Trend or Mean Rev)
        - 0-2 Filters
        - 1 Exit/Risk Logic
        """
        blocks = []

        # 1. Core Logic
        core_type = random.choice(cls.TREND_BLOCKS + cls.MEAN_REV_BLOCKS)
        blocks.append({"type": core_type, "params": cls.random_params(core_type)})

        # 2. Filters (Optional)
        if random.random() > 0.5:
            filter_type = random.choice(cls.FILTERS)
            blocks.append({"type": filter_type, "params": cls.random_params(filter_type)})

        # 3. Risk (Always have one)
        risk_type = random.choice(cls.VOLATILITY_BLOCKS)
        blocks.append({"type": risk_type, "params": cls.random_params(risk_type)})

        # Generate ID
        # Canonicalize to avoid dupes: sort blocks by type? No, order matters for logic sometimes, but here blocks are components.
        # We will serialize and hash.
        raw = json.dumps(blocks, sort_keys=True)
        sid = hashlib.md5(raw.encode()).hexdigest()[:8]

        return StrategyCandidate(id=sid, blocks=blocks)

