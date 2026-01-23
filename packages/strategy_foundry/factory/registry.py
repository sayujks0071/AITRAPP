from typing import List
import json
import os
from packages.strategy_foundry.factory.grammar import Strategy

class CandidateRegistry:
    def __init__(self, run_dir: str):
        self.run_dir = run_dir

    def save_candidates(self, filename: str, candidates: List[Strategy]):
        path = os.path.join(self.run_dir, filename)
        with open(path, "w") as f:
            json.dump([c.to_dict() for c in candidates], f, indent=2)

    def load_candidates(self, filename: str) -> List[Strategy]:
        path = os.path.join(self.run_dir, filename)
        if not os.path.exists(path):
            return []
        with open(path, "r") as f:
            data = json.load(f)
        return [Strategy.from_dict(d) for d in data]
