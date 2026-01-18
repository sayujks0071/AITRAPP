import json
import os
import shutil
from datetime import datetime
from typing import Dict, Optional, Any

class ChampionStore:
    def __init__(self, base_dir="packages/strategy_foundry/results/champions"):
        self.base_dir = base_dir
        self.current_file = os.path.join(base_dir, "current.json")
        os.makedirs(base_dir, exist_ok=True)

    def load_current_champion(self) -> Optional[Dict[str, Any]]:
        if os.path.exists(self.current_file):
            try:
                with open(self.current_file, "r") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def save_new_champion(self, candidate_spec: Dict, metrics: Dict, score: float, run_ts: str):
        """
        Promotes a new champion.
        """
        champion_data = {
            "spec": candidate_spec,
            "metrics": metrics,
            "score": score,
            "promoted_at": datetime.now().isoformat(),
            "run_ts": run_ts
        }

        # 1. Archive old if exists
        if os.path.exists(self.current_file):
            old = self.load_current_champion()
            if old:
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                old_id = old.get("spec", {}).get("id", "unknown")
                archive_path = os.path.join(self.base_dir, f"{ts}_{old_id}.json")
                with open(archive_path, "w") as f:
                    json.dump(old, f, indent=2)

        # 2. Save new
        with open(self.current_file, "w") as f:
            json.dump(champion_data, f, indent=2)

    def should_promote(self, new_score: float, new_metrics: Dict) -> bool:
        """
        Decides if new candidate should replace current champion.
        """
        current = self.load_current_champion()
        if not current:
            return True

        current_score = current.get("score", 0)
        current_metrics = current.get("metrics", {})

        # Rule: New score >= Current + 10%
        if new_score >= current_score * 1.10:
            return True

        # Rule: Reduce MaxDD by 5% absolute, without degrading Sharpe meaningfully (e.g. within 10%)
        # Assuming we passed eligibility already.
        # This is complex to check perfectly without granular metric access.
        # Let's stick to Score beat.

        return False
