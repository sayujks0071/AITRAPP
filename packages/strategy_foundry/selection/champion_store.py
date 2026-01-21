import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


class ChampionStore:
    def __init__(self, base_dir="packages/strategy_foundry/results/champions"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def _get_current_file(self, instrument: str) -> str:
        return os.path.join(self.base_dir, f"current_{instrument}.json")

    def load_current_champion(self, instrument: str) -> Optional[Dict[str, Any]]:
        path = self._get_current_file(instrument)
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def save_new_champion(self, candidate_spec: Dict, metrics: Dict, score: float, run_ts: str, instrument: str):
        """
        Promotes a new champion.
        """
        champion_data = {
            "spec": candidate_spec,
            "metrics": metrics,
            "score": score,
            "promoted_at": datetime.now().isoformat(),
            "run_ts": run_ts,
            "instrument": instrument
        }

        current_file = self._get_current_file(instrument)

        # 1. Archive old if exists
        if os.path.exists(current_file):
            old = self.load_current_champion(instrument)
            if old:
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                old_id = old.get("spec", {}).get("id", "unknown")
                archive_path = os.path.join(self.base_dir, f"{ts}_{instrument}_{old_id}.json")
                with open(archive_path, "w") as f:
                    json.dump(old, f, indent=2)

        # 2. Save new
        with open(current_file, "w") as f:
            json.dump(champion_data, f, indent=2)

    def should_promote(self, new_score: float, new_metrics: Dict, instrument: str) -> bool:
        """
        Decides if new candidate should replace current champion.
        """
        current = self.load_current_champion(instrument)
        if not current:
            return True

        current_score = current.get("score", 0)
        current_metrics = current.get("metrics", {})

        # Rule 1: New score >= Current + 10%
        if new_score >= current_score * 1.10:
            return True

        # Rule 2: Reduce MaxDD by >= 5% absolute, Sharpe within 10%
        new_dd = new_metrics.get("max_dd", 1.0)
        curr_dd = current_metrics.get("max_dd", 1.0)
        new_sharpe = new_metrics.get("sharpe", 0.0)
        curr_sharpe = current_metrics.get("sharpe", 0.0)

        # Reduce MaxDD by >= 5% absolute (e.g. 0.25 -> 0.20)
        if (curr_dd - new_dd) >= 0.05:
            # Sharpe not degrading meaningfully (>= 90% of current)
            if new_sharpe >= curr_sharpe * 0.90:
                 return True

        return False
