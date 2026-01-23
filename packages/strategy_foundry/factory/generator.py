import hashlib
import json
import random
import time
from typing import List
from packages.strategy_foundry.factory.grammar import (
    StrategyCandidate, StrategyComponent, EntryType, RiskType, FilterType
)

class StrategyGenerator:
    def __init__(self, seed: int = None):
        self.rng = random.Random(seed) if seed is not None else random.Random()

    def generate_candidates(self, n: int = 10) -> List[StrategyCandidate]:
        candidates = []
        for _ in range(n):
            candidates.append(self._generate_single())
        return candidates

    def _generate_single(self) -> StrategyCandidate:
        # 1. Entry
        entry_type = self.rng.choice(list(EntryType))
        entry_params = {}

        if entry_type == EntryType.BREAKOUT:
            entry_params = {
                "period": self.rng.choice([10, 20, 50]),
                "mult": self.rng.choice([1.0, 1.5, 2.0])
            }
        elif entry_type == EntryType.TREND:
            entry_params = {
                "fast_period": self.rng.choice([9, 20]),
                "slow_period": self.rng.choice([20, 50]),
                "signal_type": self.rng.choice(["CROSS", "SLOPE"])
            }
        elif entry_type == EntryType.MEAN_REVERSION:
            entry_params = {
                "rsi_period": self.rng.choice([7, 14]),
                "rsi_threshold": self.rng.choice([20, 30])
            }

        entry = StrategyComponent(type=entry_type.value, params=entry_params)

        # 2. Exit (Risk)
        exit_type = RiskType.ATR_STOP # Default to ATR Stop for now as primary
        exit_params = {
            "atr_period": 14,
            "stop_mult": self.rng.choice([1.5, 2.0, 3.0]),
            "tp_mult": self.rng.choice([0.0, 2.0, 3.0, 5.0]), # 0 means no TP (let it run)
            "trail": self.rng.choice([True, False])
        }
        exit_comp = StrategyComponent(type=exit_type.value, params=exit_params)

        # 3. Filters
        filters = []
        if self.rng.random() < 0.5:
            filters.append(StrategyComponent(
                type=FilterType.REGIME_MA.value,
                params={"period": 200, "timeframe": "1D"}
            ))

        # 4. ID Generation (Stable hash)
        # We hash the string representation of components to ensure same config = same ID
        struct = {
            "entry": entry.model_dump(),
            "exit": exit_comp.model_dump(),
            "filters": [f.model_dump() for f in filters]
        }
        struct_str = json.dumps(struct, sort_keys=True)
        strat_id = hashlib.sha1(struct_str.encode()).hexdigest()[:12]

        return StrategyCandidate(
            id=strat_id,
            entry=entry,
            exit=exit_comp,
            filters=filters,
            generation_ts=time.time()
        )
