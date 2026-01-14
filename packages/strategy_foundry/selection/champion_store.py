import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

CHAMPION_DIR = Path("packages/strategy_foundry/results/champions")

def save_champion(candidate: Dict[str, Any], metrics: Dict[str, Any], spec: Dict[str, Any]):
    CHAMPION_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        "timestamp": datetime.now().isoformat(),
        "candidate_id": candidate.get("strategy_id"),
        "metrics": metrics,
        "spec": spec,
        "blended_score": candidate.get("score", 0)
    }

    # Save current
    with open(CHAMPION_DIR / "current.json", "w") as f:
        json.dump(data, f, indent=2)

    # Archive
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{ts_str}_{candidate.get('strategy_id')}.json"
    with open(CHAMPION_DIR / fname, "w") as f:
        json.dump(data, f, indent=2)

def load_champion() -> Optional[Dict[str, Any]]:
    path = CHAMPION_DIR / "current.json"
    if not path.exists():
        return None

    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None
