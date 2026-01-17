import os
import json
import time
from typing import Optional, Dict
from packages.strategy_foundry.factory.grammar import StrategyCandidate

class ChampionStore:
    def __init__(self, champions_dir: str):
        self.champions_dir = champions_dir
        self.current_file = os.path.join(champions_dir, "current.json")
        os.makedirs(champions_dir, exist_ok=True)

    def load_current(self) -> Optional[StrategyCandidate]:
        if not os.path.exists(self.current_file):
            return None
        try:
            with open(self.current_file, "r") as f:
                data = json.load(f)
            return StrategyCandidate(**data['candidate'])
        except Exception:
            return None

    def load_current_metadata(self) -> Dict:
        if not os.path.exists(self.current_file):
            return {}
        try:
            with open(self.current_file, "r") as f:
                data = json.load(f)
            return data
        except Exception:
            return {}

    def promote_new_champion(self, candidate: StrategyCandidate, metrics: Dict, score: float):
        # Save historical version
        timestamp = int(time.time())
        filename = f"{timestamp}_{candidate.id}.json"

        data = {
            "promoted_at": timestamp,
            "score": score,
            "metrics": metrics,
            "candidate": candidate.to_dict()
        }

        # Save history
        with open(os.path.join(self.champions_dir, filename), "w") as f:
            json.dump(data, f, indent=2)

        # Update current
        with open(self.current_file, "w") as f:
            json.dump(data, f, indent=2)
