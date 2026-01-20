import json
import os
from typing import List, Dict, Any

class CandidateRegistry:
    """Manages strategy candidates"""

    def __init__(self, registry_path: str = None):
        self.registry_path = registry_path
        self.candidates = {}

    def add_candidates(self, candidates: List[Dict[str, Any]]):
        for c in candidates:
            self.candidates[c["id"]] = c

    def save(self, filepath: str):
        with open(filepath, "w") as f:
            json.dump(list(self.candidates.values()), f, indent=2)

    def load(self, filepath: str):
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                cands = json.load(f)
                self.add_candidates(cands)
