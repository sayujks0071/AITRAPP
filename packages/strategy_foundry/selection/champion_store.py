import json
from pathlib import Path
from typing import Dict, Any, Optional

CHAMPION_DIR = Path(__file__).parent.parent / "results" / "champions"
CHAMPION_DIR.mkdir(parents=True, exist_ok=True)

class ChampionStore:
    def load_champion(self, instrument: str = "NIFTY") -> Optional[Dict[str, Any]]:
        path = CHAMPION_DIR / f"current_{instrument}.json"
        if path.exists():
            return json.loads(path.read_text())
        return None

    def save_champion(self, candidate, metrics: Dict[str, Any], instrument: str = "NIFTY", timestamp: str = ""):
        data = {
            "id": candidate.id,
            "candidate": candidate.to_json(),
            "metrics": metrics,
            "timestamp": timestamp,
            "instrument": instrument
        }

        # Save current
        path = CHAMPION_DIR / f"current_{instrument}.json"
        path.write_text(json.dumps(data, indent=2))

        # Save versioned
        vpath = CHAMPION_DIR / f"{timestamp}_{candidate.id}.json"
        vpath.write_text(json.dumps(data, indent=2))

    def is_better(self, new_metrics: Dict[str, Any], current_metrics: Dict[str, Any], ranker) -> bool:
        new_score = ranker.score(new_metrics)
        curr_score = ranker.score(current_metrics)

        # Rule: Must exceed by 10% OR significantly lower MaxDD
        if new_score > curr_score * 1.1:
            return True

        if new_metrics['max_dd'] < current_metrics['max_dd'] * 0.7 and new_score > curr_score * 0.9:
            return True

        return False
