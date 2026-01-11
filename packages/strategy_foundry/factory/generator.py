"""Strategy Generator"""
import random
from typing import List
from packages.strategy_foundry.factory.grammar import StrategyConfig, StrategyRule, BLOCK_TYPES, PARAM_RANGES

class StrategyGenerator:
    def __init__(self, seed: int = None):
        if seed is not None:
            random.seed(seed)

    def generate(self, count: int = 1) -> List[StrategyConfig]:
        strategies = []
        seen_ids = set()

        attempts = 0
        while len(strategies) < count and attempts < count * 10:
            attempts += 1
            strat = self._generate_one()
            sid = strat.get_id()
            if sid not in seen_ids:
                seen_ids.add(sid)
                strategies.append(strat)

        return strategies

    def _generate_one(self) -> StrategyConfig:
        # 1. Pick Entry Logic
        entry_type = random.choice(BLOCK_TYPES["ENTRY"])
        entry_rule = StrategyRule(entry_type, self._sample_params(entry_type))

        # 2. Pick Exit Logic
        # Always include Session Exit
        exit_rules = []

        # Basic Stop
        stop_type = "STOP_ATR"
        exit_rules.append(StrategyRule(stop_type, self._sample_params(stop_type)))

        # Optional Target or Time Stop
        if random.random() > 0.5:
             target_type = "TARGET_FIXED"
             exit_rules.append(StrategyRule(target_type, self._sample_params(target_type)))

        if random.random() > 0.7:
             time_stop = "STOP_TIME"
             exit_rules.append(StrategyRule(time_stop, self._sample_params(time_stop)))

        # Mandatory Session Exit
        exit_rules.append(StrategyRule("EXIT_SESSION", self._sample_params("EXIT_SESSION")))

        # 3. Pick Filters (Optional)
        filters = []
        if random.random() > 0.5:
            filter_type = random.choice(BLOCK_TYPES["FILTER"])
            filters.append(StrategyRule(filter_type, self._sample_params(filter_type)))

        return StrategyConfig(
            entry_rules=[entry_rule],
            exit_rules=exit_rules,
            filters=filters
        )

    def _sample_params(self, block_type: str) -> dict:
        ranges = PARAM_RANGES.get(block_type, {})
        params = {}
        for k, v in ranges.items():
            if isinstance(v, list):
                params[k] = random.choice(v)
            else:
                params[k] = v
        return params
