"""Strategy Generator"""
import random
import hashlib
import json
from packages.strategy_foundry.factory.grammar import (
    StrategyCandidate, EntryType, FilterType, ExitType
)

class StrategyGenerator:
    def __init__(self, seed: int = None):
        if seed:
            random.seed(seed)

    def _generate_params(self, block_type: str) -> dict:
        """Generate random parameters for a block type"""
        if block_type == EntryType.ORB_BREAKOUT:
            return {
                "window_minutes": random.choice([15, 30, 60])
            }
        elif block_type == EntryType.DONCHIAN_BREAKOUT:
            return {
                "period": random.choice([10, 20, 50])
            }
        elif block_type == EntryType.EMA_CROSS:
            fast = random.choice([5, 9, 13])
            slow = random.choice([21, 34, 55])
            if fast >= slow: slow = fast + 5
            return {"fast": fast, "slow": slow}
        elif block_type == EntryType.SUPERTREND:
            return {
                "period": random.choice([7, 10, 14]),
                "multiplier": random.choice([2.0, 3.0])
            }
        elif block_type == EntryType.RSI_OVERSOLD:
            return {
                "period": 14,
                "threshold": random.choice([20, 30, 40])
            }
        elif block_type == EntryType.BOLLINGER_REVERSION:
             return {
                 "period": 20,
                 "std": 2.0
             }

        # Filters
        elif block_type == FilterType.REGIME_SMA:
            return {"period": random.choice([50, 100, 200])}
        elif block_type == FilterType.ADX_FILTER:
            return {"period": 14, "threshold": random.choice([20, 25])}

        # Exits
        elif block_type == ExitType.STOP_LOSS_ATR:
            return {"period": 14, "mult": random.choice([1.5, 2.0, 3.0])}
        elif block_type == ExitType.TIME_STOP:
            return {"bars": random.choice([12, 24, 48])} # e.g. 1 hour, 2 hours on 5m

        return {}

    def generate(self, n=1) -> list[StrategyCandidate]:
        candidates = []
        for _ in range(n):
            # 1. Entry
            entry_type = random.choice(list(EntryType))
            entry_block = {
                "type": entry_type,
                "params": self._generate_params(entry_type)
            }

            # 2. Filters (0 to 2)
            filters = []
            if random.random() > 0.3:
                f_type = random.choice(list(FilterType))
                filters.append({"type": f_type, "params": self._generate_params(f_type)})

            # 3. Exits
            exits = []
            # Always ATR Stop
            exits.append({
                "type": ExitType.STOP_LOSS_ATR,
                "params": self._generate_params(ExitType.STOP_LOSS_ATR)
            })
            # Optional Time Stop
            if random.random() > 0.5:
                exits.append({
                    "type": ExitType.TIME_STOP,
                    "params": self._generate_params(ExitType.TIME_STOP)
                })
            # Mandatory Session Close
            exits.append({
                "type": ExitType.SESSION_CLOSE,
                "params": {"time": "15:25"}
            })

            # Create ID
            struct = {"entry": entry_block, "filters": filters, "exits": exits}
            struct_json = json.dumps(struct, sort_keys=True)
            candidate_id = hashlib.md5(struct_json.encode()).hexdigest()[:8]

            cand = StrategyCandidate(
                id=candidate_id,
                source_grammar="v1",
                entry_block=entry_block,
                filter_blocks=filters,
                exit_blocks=exits
            )
            candidates.append(cand)

        return candidates
