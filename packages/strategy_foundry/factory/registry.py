"""Strategy Registry"""
from typing import Dict
from .generator import StrategyCandidate

class Registry:
    def __init__(self):
        self.strategies: Dict[str, StrategyCandidate] = {}

    def add(self, strategy: StrategyCandidate):
        self.strategies[strategy.id] = strategy

    def get(self, id: str) -> StrategyCandidate:
        return self.strategies.get(id)
