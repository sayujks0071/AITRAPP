from typing import List
from .grammar import Strategy, SimpleTrendStrategy, MeanReversionStrategy
from .parameter_space import ParameterSpace
import structlog

logger = structlog.get_logger(__name__)

class StrategyGenerator:
    def __init__(self, count: int = 50):
        self.count = count

    def generate(self) -> List[Strategy]:
        strategies = []
        seen_ids = set()

        for _ in range(self.count * 2): # Try 2x to hit count
            if len(strategies) >= self.count:
                break

            # Randomly pick type
            import random
            if random.random() < 0.6: # Favor trend
                params = ParameterSpace.get_random_trend_params()
                strat = SimpleTrendStrategy(params)
            else:
                params = ParameterSpace.get_random_mean_rev_params()
                strat = MeanReversionStrategy(params)

            sid = strat.get_id()
            if sid not in seen_ids:
                seen_ids.add(sid)
                strategies.append(strat)

        logger.info(f"Generated {len(strategies)} unique strategies")
        return strategies
