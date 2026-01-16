import json
import os
from typing import List
from packages.strategy_foundry.factory.grammar import StrategyConfig

class CandidateRegistry:
    @staticmethod
    def save_candidates(candidates: List[StrategyConfig], filepath: str):
        data = [c.to_dict() for c in candidates]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_candidates(filepath: str) -> List[StrategyConfig]:
        if not os.path.exists(filepath):
            return []
        with open(filepath, 'r') as f:
            data = json.load(f)
        return [StrategyConfig.from_dict(d) for d in data]
