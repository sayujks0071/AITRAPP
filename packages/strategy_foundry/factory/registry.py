import json
import os
from typing import List

from .grammar import StrategyCandidate


class CandidateRegistry:
    def __init__(self, run_dir: str):
        self.run_dir = run_dir
        self.candidates_file = os.path.join(run_dir, "candidates.json")

    def save_candidates(self, candidates: List[StrategyCandidate]):
        data = [c.to_dict() for c in candidates]
        with open(self.candidates_file, "w") as f:
            json.dump(data, f, indent=2)

    def load_candidates(self) -> List[StrategyCandidate]:
        if not os.path.exists(self.candidates_file):
            return []
        with open(self.candidates_file, "r") as f:
            data = json.load(f)
        return [StrategyCandidate(**d) for d in data]
