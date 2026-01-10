"""Strategy Generator"""
import random
from typing import List
from .grammar import StrategyConfig, Rule, TrendFollowBlock, MeanReversionBlock, RiskBlock

class StrategyGenerator:
    """Generates random strategies based on grammar"""

    def generate(self, n: int = 1) -> List[StrategyConfig]:
        strategies = []
        seen_ids = set()

        attempts = 0
        while len(strategies) < n and attempts < n * 10:
            attempts += 1
            strat = self._create_random_strategy()
            sid = strat.get_id()

            if sid not in seen_ids:
                seen_ids.add(sid)
                strategies.append(strat)

        return strategies

    def _create_random_strategy(self) -> StrategyConfig:
        # Decide type: Trend or Mean Rev (50/50)
        is_trend = random.random() > 0.5

        entry_rules = []
        exit_rules = [] # Often implicit in entry (reverse signal) or explicit

        if is_trend:
            block_type = random.choice(TrendFollowBlock.TYPES)
            params = self._sample_params(TrendFollowBlock.get_params(block_type))
            entry_rules.append(Rule(block_type, params))
        else:
            block_type = random.choice(MeanReversionBlock.TYPES)
            params = self._sample_params(MeanReversionBlock.get_params(block_type))
            entry_rules.append(Rule(block_type, params))

        # Always add a risk rule
        risk_type = "ATR_STOP" # random.choice(RiskBlock.TYPES)
        risk_params = self._sample_params(RiskBlock.get_params(risk_type))
        risk_rules = [Rule(risk_type, risk_params)]

        return StrategyConfig(entry_rules, exit_rules, risk_rules)

    def _sample_params(self, param_space):
        """Pick random values from lists in param_space"""
        result = {}
        for k, v in param_space.items():
            if isinstance(v, list):
                result[k] = random.choice(v)
            else:
                result[k] = v
        return result
