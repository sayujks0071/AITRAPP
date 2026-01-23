import json
import os
from typing import Dict, Optional
from pathlib import Path
import shutil
from datetime import datetime
import structlog
from packages.strategy_foundry.factory.grammar import StrategyCandidate

logger = structlog.get_logger(__name__)

class ChampionStore:
    def __init__(self, champions_dir: str = "packages/strategy_foundry/results/champions"):
        self.champions_dir = Path(champions_dir)
        self.champions_dir.mkdir(parents=True, exist_ok=True)

    def get_champion_path(self, instrument: str) -> Path:
        return self.champions_dir / f"champion_{instrument}.json"

    def load_champion(self, instrument: str) -> Optional[Dict]:
        path = self.get_champion_path(instrument)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load champion", instrument=instrument, error=str(e))
            return None

    def save_champion(self, instrument: str, candidate: StrategyCandidate, metrics: Dict, score: float):
        path = self.get_champion_path(instrument)

        # Archive current if exists
        if path.exists():
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = self.champions_dir / f"archive_{instrument}_{ts}.json"
            shutil.copy(path, archive_path)

        data = {
            "instrument": instrument,
            "candidate": candidate.model_dump(),
            "metrics": metrics,
            "score": score,
            "updated_at": datetime.now().isoformat()
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info("Champion saved", instrument=instrument, id=candidate.id, score=score)

    def check_promotion(self, current_champ: Dict, challenger_metrics: Dict, challenger_score: float) -> bool:
        """
        Check if challenger should promote over current champion.
        Rule: Beat blended_score by >= 10% OR reduce MaxDD by >= 5% absolute (keeping Sharpe stable).
        """
        if not current_champ:
            return True # No champion, automatic promotion

        current_score = current_champ.get("score", 0.0)

        # Score improvement
        if challenger_score >= current_score * 1.10:
            logger.info("Promotion: Score beat", current=current_score, new=challenger_score)
            return True

        # Drawdown improvement
        current_dd = current_champ["metrics"].get("max_dd", -1.0)
        new_dd = challenger_metrics.get("max_dd", -1.0)

        # Note: DD is negative. -0.20 vs -0.25. -0.20 is better (larger).
        # "Reduce MaxDD" means make it less negative (closer to 0).
        # So New DD > Current DD + 0.05
        # e.g. -0.15 > -0.20 + 0.05 (-0.15) -> True
        if new_dd > (current_dd + 0.05):
             # Ensure Sharpe didn't drop too much (e.g. > 10% drop)
             current_sharpe = current_champ["metrics"].get("sharpe", 0.0)
             new_sharpe = challenger_metrics.get("sharpe", 0.0)
             if new_sharpe >= current_sharpe * 0.9:
                 logger.info("Promotion: DD improved", current_dd=current_dd, new_dd=new_dd)
                 return True

        return False
