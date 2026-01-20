import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ChampionStore:
    def __init__(self, champions_dir="packages/strategy_foundry/results/champions"):
        self.champions_dir = champions_dir
        self.current_file = os.path.join(champions_dir, "current.json")
        os.makedirs(champions_dir, exist_ok=True)

    def get_champion(self, instrument: str) -> Dict[str, Any]:
        """Load current champion for instrument"""
        if os.path.exists(self.current_file):
            with open(self.current_file, "r") as f:
                all_champs = json.load(f)
                return all_champs.get(instrument)
        return None

    def save_champion(self, instrument: str, candidate: Dict[str, Any], score: float, metrics: Dict[str, Any]):
        """Save new champion"""
        # Load existing
        all_champs = {}
        if os.path.exists(self.current_file):
            try:
                with open(self.current_file, "r") as f:
                    all_champs = json.load(f)
            except:
                pass

        # Update
        entry = {
            "candidate": candidate,
            "score": score,
            "metrics": metrics,
            "promoted_at": self._get_timestamp()
        }
        all_champs[instrument] = entry

        # Save Current
        with open(self.current_file, "w") as f:
            json.dump(all_champs, f, indent=2)

        # Archive
        archive_name = f"{instrument}_{entry['promoted_at']}_{candidate['id']}.json"
        with open(os.path.join(self.champions_dir, archive_name), "w") as f:
            json.dump(entry, f, indent=2)

        logger.info(f"New Champion promoted for {instrument}: {candidate['id']} (Score: {score:.2f})")

    def should_promote(self, instrument: str, new_score: float, new_metrics: Dict[str, Any]) -> bool:
        """
        Promotion rule:
        - Must exceed current score by >= 10%
        - OR Lower MaxDD materially (>= 5% absolute reduction) without degrading Sharpe > 10%
        """
        current = self.get_champion(instrument)
        if not current:
            return True

        current_score = current["score"]
        current_metrics = current["metrics"]

        # Rule 1: Score improvement
        if new_score >= current_score * 1.10:
            logger.info(f"Promoting: Score {new_score:.2f} beats {current_score:.2f} by >10%")
            return True

        # Rule 2: Risk reduction
        curr_dd = current_metrics.get("max_dd", 1.0)
        new_dd = new_metrics.get("max_dd", 1.0)

        if (curr_dd - new_dd) >= 0.05: # 5% absolute reduction
             # Check Sharpe degradation
             curr_sharpe = current_metrics.get("sharpe", 0)
             new_sharpe = new_metrics.get("sharpe", 0)

             if new_sharpe >= curr_sharpe * 0.90:
                 logger.info("Promoting: MaxDD improved by >5% with stable Sharpe")
                 return True

        return False

    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")
