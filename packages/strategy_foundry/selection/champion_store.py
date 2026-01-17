import json
import os
from typing import Dict, Any

class ChampionStore:
    def __init__(self, base_dir: str = "packages/strategy_foundry/results/champions"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def load_current_champion(self) -> Dict[str, Any]:
        path = os.path.join(self.base_dir, "current.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return {}

    def save_champion(self, champion: Dict[str, Any]):
        path = os.path.join(self.base_dir, "current.json")
        with open(path, "w") as f:
            json.dump(champion, f, indent=2)

        # Versioned
        ts = champion.get("timestamp", "unknown")
        cid = champion.get("id", "unknown")
        v_path = os.path.join(self.base_dir, f"{ts}_{cid}.json")
        with open(v_path, "w") as f:
            json.dump(champion, f, indent=2)
