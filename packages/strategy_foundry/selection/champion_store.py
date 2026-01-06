"""Champion persistence"""
import json
import shutil
from pathlib import Path
from datetime import datetime
from packages.strategy_foundry.factory.grammar import StrategyCandidate

CHAMPION_DIR = Path("packages/strategy_foundry/results/champions")
CHAMPION_DIR.mkdir(parents=True, exist_ok=True)

class ChampionStore:
    def load_current(self) -> dict:
        p = CHAMPION_DIR / "current.json"
        if p.exists():
            return json.loads(p.read_text())
        return {}

    def save_new_champion(self, candidate: StrategyCandidate, metrics: dict, score: float):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        data = {
            "id": candidate.id,
            "candidate": {
                "entry_logic": candidate.entry_logic,
                "exit_logic": candidate.exit_logic,
                "filters": candidate.filters,
                "timeframe": candidate.timeframe,
                "params": candidate.params
            },
            "metrics": metrics,
            "score": score,
            "timestamp": ts
        }

        # Save versioned
        (CHAMPION_DIR / f"{ts}_{candidate.id}.json").write_text(json.dumps(data, indent=2))

        # Update current
        (CHAMPION_DIR / "current.json").write_text(json.dumps(data, indent=2))

    def should_promote(self, new_score: float, new_metrics: dict) -> bool:
        """
        Check against current.
        Rule: Beat score by >= 10% OR reduce MaxDD by >= 5% abs (with similar Sharpe)
        """
        current = self.load_current()
        if not current:
            return True

        old_score = current.get("score", 0.0)
        old_dd = current.get("metrics", {}).get("global", {}).get("max_drawdown", 1.0)

        if new_score >= old_score * 1.10:
            return True

        new_dd = new_metrics.get("global", {}).get("max_drawdown", 1.0)
        if (old_dd - new_dd) >= 0.05 and new_score >= old_score * 0.9:
            return True

        return False
