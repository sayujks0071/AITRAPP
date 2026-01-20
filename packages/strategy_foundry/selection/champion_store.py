"""Manages champion persistence and promotion"""
import json
import os
import shutil
from datetime import datetime
from typing import Optional, Dict

class ChampionStore:
    def __init__(self, base_dir: str = "packages/strategy_foundry/results/champions"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.current_path = os.path.join(self.base_dir, "current.json")

    def load_current(self) -> Optional[Dict]:
        if os.path.exists(self.current_path):
            try:
                with open(self.current_path, "r") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def save_champion(self, candidate_dict: Dict, metrics: Dict, score: float):
        """
        Save new champion.
        """
        data = {
            "timestamp": datetime.now().isoformat(),
            "candidate": candidate_dict,
            "metrics": metrics,
            "score": score
        }

        # Save as current
        with open(self.current_path, "w") as f:
            json.dump(data, f, indent=2)

        # Save versioned
        ts_safe = datetime.now().strftime("%Y%m%d_%H%M%S")
        cid = candidate_dict["id"]
        v_path = os.path.join(self.base_dir, f"{ts_safe}_{cid}.json")
        with open(v_path, "w") as f:
            json.dump(data, f, indent=2)

    def should_promote(self, new_score: float, new_dd: float, new_sharpe: float) -> bool:
        """
        Promotion rule:
        - New must beat current blended_score by >= 10%
        - OR reduce MaxDD by >= 5% absolute while not degrading Sharpe meaningfully.
        """
        current = self.load_current()
        if not current:
            return True

        curr_score = current.get("score", -99)
        curr_metrics = current.get("metrics", {})
        curr_dd = curr_metrics.get("max_dd", -1.0) # usually negative
        curr_sharpe = curr_metrics.get("avg_sharpe", 0)

        # Score improvement
        if new_score > curr_score * 1.10:
            return True

        # DD improvement (MaxDD is negative, so closer to 0 is better)
        # e.g. Current -30%, New -20%. diff = (-0.20) - (-0.30) = +0.10 > 0.05
        if (new_dd - curr_dd) > 0.05:
            # Check Sharpe not degraded meaningfully (e.g. > 90% of current)
            if new_sharpe >= curr_sharpe * 0.9:
                return True

        return False
