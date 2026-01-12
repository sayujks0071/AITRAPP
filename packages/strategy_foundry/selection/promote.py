import json
from pathlib import Path
from typing import Dict, Optional
import structlog
import pandas as pd
from packages.strategy_foundry.factory.grammar import StrategyCandidate

logger = structlog.get_logger(__name__)

RESULTS_DIR = Path(__file__).parent.parent / "results"
CHAMPIONS_DIR = RESULTS_DIR / "champions"

class Promoter:
    def __init__(self, config: Dict):
        self.config = config
        CHAMPIONS_DIR.mkdir(parents=True, exist_ok=True)

    def load_champion(self, timeframe: str) -> Optional[Dict]:
        path = CHAMPIONS_DIR / f"current_{timeframe}.json"
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def promote(self, candidate_row: pd.Series, timeframe: str) -> bool:
        """
        Check if candidate should be promoted to champion.
        """
        current_champ = self.load_champion(timeframe)

        new_score = candidate_row["score"]
        new_sharpe = candidate_row["sharpe"]
        new_dd = candidate_row["max_dd"]

        # Promotion Logic
        # New must beat current blended_score by >= 10% OR reduce MaxDD by >= 5% absolute

        should_promote = False

        if current_champ is None:
            # First champion!
            # Must meet min standards
            min_sharpe = self.config["ranking"]["promote_sharpe_min"]
            max_dd = self.config["ranking"]["promote_dd_max"]

            if new_sharpe >= min_sharpe and new_dd <= max_dd:
                should_promote = True
        else:
            curr_score = current_champ["score"]
            curr_dd = current_champ["metrics"]["max_dd_pct"]

            score_impr = (new_score - curr_score) / curr_score if curr_score > 0 else 0.11
            dd_impr = curr_dd - new_dd

            if score_impr >= 0.10:
                should_promote = True
            elif dd_impr >= 5.0 and new_sharpe >= (current_champ["metrics"]["sharpe"] * 0.9):
                should_promote = True

        if should_promote:
            self._save_champion(candidate_row, timeframe)
            return True

        return False

    def _save_champion(self, row: pd.Series, timeframe: str):
        c: StrategyCandidate = row["candidate_obj"]

        data = {
            "id": c.id,
            "candidate": c.to_json(), # String
            "metrics": {
                "score": float(row["score"]),
                "sharpe": float(row["sharpe"]),
                "max_dd_pct": float(row["max_dd"]),
                "calmar": float(row["calmar"]),
                "trades": int(row["trades"])
            },
            "score": float(row["score"]),
            "timestamp": pd.Timestamp.now().isoformat()
        }

        # Save Current
        with open(CHAMPIONS_DIR / f"current_{timeframe}.json", "w") as f:
            json.dump(data, f, indent=2)

        # Save History
        ts = int(pd.Timestamp.now().timestamp())
        with open(CHAMPIONS_DIR / f"{timeframe}_{ts}_{c.id}.json", "w") as f:
            json.dump(data, f, indent=2)

        logger.info("New Champion Promoted!", timeframe=timeframe, id=c.id, score=row["score"])
