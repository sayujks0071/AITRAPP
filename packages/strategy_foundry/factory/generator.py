"""
Strategy Generator.
"""
from packages.strategy_foundry.factory.grammar import Grammar, StrategyConfig
from typing import List

class StrategyGenerator:
    def __init__(self):
        self.grammar = Grammar()

    def generate_candidates(self, n: int, timeframe: str) -> List[StrategyConfig]:
        candidates = []
        ids = set()
        attempts = 0
        while len(candidates) < n and attempts < n * 5:
            cand = self.grammar.generate_random(timeframe)
            if cand.id not in ids:
                candidates.append(cand)
                ids.add(cand.id)
            attempts += 1
        return candidates
