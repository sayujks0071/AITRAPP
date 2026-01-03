from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import random
import hashlib

@dataclass
class StrategyCandidate:
    id: str
    entry_rules: List[Dict[str, Any]]
    exit_rules: List[Dict[str, Any]]
    filters: List[Dict[str, Any]]
    timeframe: str
    instrument: str

    def to_dict(self):
        return {
            "id": self.id,
            "entry_rules": self.entry_rules,
            "exit_rules": self.exit_rules,
            "filters": self.filters,
            "timeframe": self.timeframe,
            "instrument": self.instrument
        }

class StrategyGenerator:
    def __init__(self, instrument="NIFTY", timeframe="15m"):
        self.instrument = instrument
        self.timeframe = timeframe

    def generate(self, n=1) -> List[StrategyCandidate]:
        candidates = []
        for _ in range(n):
            candidate = self._create_candidate()
            candidates.append(candidate)
        return candidates

    def _create_candidate(self) -> StrategyCandidate:
        # Randomly select entry logic
        entry_type = random.choice(["trend_ema_cross", "breakout_donchian", "mean_reversion_rsi"])

        entry_rules = []
        if entry_type == "trend_ema_cross":
            entry_rules.append({
                "type": "ema_cross",
                "fast": random.choice([10, 20]),
                "slow": random.choice([50, 200])
            })
        elif entry_type == "breakout_donchian":
             entry_rules.append({
                "type": "donchian_breakout",
                "period": random.choice([20, 50])
            })
        elif entry_type == "mean_reversion_rsi":
            entry_rules.append({
                "type": "rsi_reversion",
                "period": 14,
                "threshold_low": random.choice([20, 30]),
                "threshold_high": random.choice([70, 80])
            })

        # Always add time exit/flat logic (enforced in engine, but here as params)
        exit_rules = [
            {"type": "stop_loss_atr", "multiplier": random.choice([1.5, 2.0, 3.0])},
            {"type": "take_profit_atr", "multiplier": random.choice([3.0, 5.0, 10.0])}, # Asymmetric R:R
            {"type": "time_stop", "bars": random.choice([12, 24])} # e.g. 3 hours or 6 hours on 15m
        ]

        # Filters
        filters = []
        if random.random() > 0.5:
             filters.append({"type": "adx_filter", "threshold": 20})

        # Generate ID
        # Stable ID based on rules
        rules_str = str(entry_rules) + str(exit_rules) + str(filters) + self.timeframe + self.instrument
        cid = hashlib.md5(rules_str.encode()).hexdigest()[:8]

        return StrategyCandidate(
            id=cid,
            entry_rules=entry_rules,
            exit_rules=exit_rules,
            filters=filters,
            timeframe=self.timeframe,
            instrument=self.instrument
        )
