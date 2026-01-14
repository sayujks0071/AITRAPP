import random
import hashlib
import json
from typing import List
from packages.strategy_foundry.factory.grammar import StrategySpec, EntryType

class StrategyGenerator:
    def __init__(self):
        pass

    def _generate_id(self, spec_dict: dict) -> str:
        # Stable ID based on content
        s = json.dumps(spec_dict, sort_keys=True)
        return hashlib.md5(s.encode()).hexdigest()[:12]

    def generate_random(self) -> StrategySpec:
        entry_type = random.choice(list(EntryType))

        params = {}
        if entry_type == EntryType.RSI_REVERSION:
            params["period"] = random.choice([7, 10, 14])
            params["threshold"] = random.choice([20, 25, 30, 35])
        elif entry_type == EntryType.RSI_MOMENTUM:
            params["period"] = random.choice([10, 14])
            params["threshold"] = random.choice([55, 60, 65, 70])
        elif entry_type == EntryType.EMA_CROSS:
            fast = random.choice([9, 13, 20])
            slow = random.choice([34, 50, 89])
            if fast >= slow:
                slow = fast + 5
            params["fast_period"] = fast
            params["slow_period"] = slow
        elif entry_type == EntryType.DONCHIAN_BREAKOUT:
            params["period"] = random.choice([10, 20, 40, 60])
        elif entry_type == EntryType.SUPERTREND_FOLLOW:
            params["period"] = random.choice([7, 10, 14])
            params["multiplier"] = random.choice([2.0, 3.0])
        elif entry_type == EntryType.BB_REVERSION:
            params["period"] = 20
            params["std"] = 2.0 # Standard

        sl = round(random.uniform(1.0, 4.0), 1)
        tp = round(random.uniform(1.5, 6.0), 1)

        # Time exit usually for intraday
        time_exit = random.choice([None, 12, 24, 36]) # Bars (e.g. 12*5m = 60m)

        spec = StrategySpec(
            strategy_id="",
            entry_logic=entry_type.value,
            entry_params=params,
            stop_loss_atr=sl,
            take_profit_atr=tp,
            time_exit_bars=time_exit
        )
        spec.strategy_id = self._generate_id(spec.to_dict())
        return spec

    def generate_candidates(self, n: int) -> List[StrategySpec]:
        candidates = []
        seen = set()
        attempts = 0
        while len(candidates) < n and attempts < n * 5:
            cand = self.generate_random()
            if cand.strategy_id not in seen:
                candidates.append(cand)
                seen.add(cand.strategy_id)
            attempts += 1
        return candidates
