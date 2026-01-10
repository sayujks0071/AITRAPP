"""
Promotion logic for champions.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)

class Promoter:
    def __init__(self):
        self.champions_dir = Path("packages/strategy_foundry/results/champions")
        self.champions_dir.mkdir(parents=True, exist_ok=True)
        self.current_champ_file = self.champions_dir / "current.json"

    def get_current_champion(self) -> Optional[Dict[str, Any]]:
        if self.current_champ_file.exists():
            try:
                with open(self.current_champ_file, "r") as f:
                    return json.load(f)
            except:
                return None
        return None

    def try_promote(self, challenger: Dict[str, Any], timestamp: str) -> bool:
        """
        Check if challenger beats current champion.
        challenger: dict with keys [id, score, metrics, strategy]
        """
        current = self.get_current_champion()

        should_promote = False
        reason = ""

        if current is None:
            should_promote = True
            reason = "No incumbent"
        else:
            # Promotion rules
            # Beat score by 10% OR reduce MaxDD by 5% absolute (while keeping Sharpe)

            score_diff_pct = (challenger["score"] - current["score"]) / current["score"] if current["score"] > 0 else 0
            dd_improvement = current["max_dd"] - challenger["max_dd"]

            if score_diff_pct >= 0.10:
                should_promote = True
                reason = f"Score improved by {score_diff_pct:.1%}"
            elif dd_improvement >= 0.05 and challenger["sharpe"] >= current["sharpe"] * 0.9:
                should_promote = True
                reason = f"MaxDD improved by {dd_improvement:.1%} with similar Sharpe"

        if should_promote:
            logger.info("Promoting new champion", id=challenger["id"], reason=reason)
            self._save_champion(challenger, timestamp)
            return True

        return False

    def _save_champion(self, champ: Dict[str, Any], timestamp: str):
        # Save versioned
        filename = f"{timestamp}_{champ['id']}.json"
        with open(self.champions_dir / filename, "w") as f:
            # Helper to convert strategy obj to dict if needed
            if hasattr(champ["strategy"], "to_json"):
                # Strategy is an object, convert it
                 # Use asdict? But we stored 'strategy_obj' in ranker which is the object.
                 # Actually ranker stored 'strategy_obj' in 'strategy' column?
                 # Let's fix that in ranker usage or here.
                 pass

            # Serialize
            # If strategy is object, need to serialize it
            out = champ.copy()
            if hasattr(out.get("strategy"), "to_json"):
                 # It's already an object, assume we can dump it or it was stored as dict?
                 # Ranker stores "strategy" as the object.
                 # We need to extract the spec.
                 out["strategy_spec"] = json.loads(out["strategy"].to_json())
                 del out["strategy"]
            elif "strategy" in out and not isinstance(out["strategy"], dict):
                del out["strategy"] # Cannot serialize object

            json.dump(out, f, indent=2)

        # Save current
        with open(self.current_champ_file, "w") as f:
            json.dump(out, f, indent=2)
