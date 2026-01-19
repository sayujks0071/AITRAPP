"""
Registry for candidates.
"""
from typing import Dict, Optional
from packages.strategy_foundry.factory.grammar import Strategy

class CandidateRegistry:
    def __init__(self):
        self.candidates: Dict[str, Strategy] = {}

    def add(self, strategy: Strategy) -> bool:
        """Add strategy. Returns True if new, False if exists."""
        if strategy.id in self.candidates:
            return False
        self.candidates[strategy.id] = strategy
        return True

    def get(self, strategy_id: str) -> Optional[Strategy]:
        return self.candidates.get(strategy_id)

    def clear(self):
        self.candidates.clear()
