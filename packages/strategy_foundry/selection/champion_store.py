"""
Champion Store.
Manages the current champion strategy.
"""
import os
import json
import shutil
from datetime import datetime
from typing import Optional, Dict, Any
from packages.strategy_foundry.factory.grammar import StrategyCandidate

CHAMPION_DIR = "packages/strategy_foundry/results/champions"
CURRENT_FILE = os.path.join(CHAMPION_DIR, "current.json")

def load_champion() -> Optional[StrategyCandidate]:
    if not os.path.exists(CURRENT_FILE):
        return None
    try:
        with open(CURRENT_FILE, "r") as f:
            data = json.load(f)
            # data wraps the candidate
            return StrategyCandidate(id=data["id"], blocks=data["blocks"])
    except Exception:
        return None

def save_champion(candidate: StrategyCandidate, metrics: Dict[str, Any], score: float):
    # Archive old
    if os.path.exists(CURRENT_FILE):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        old_id = load_champion().id
        shutil.copy(CURRENT_FILE, os.path.join(CHAMPION_DIR, f"{ts}_{old_id}.json"))

    # Save new
    data = {
        "id": candidate.id,
        "blocks": candidate.blocks,
        "metrics": metrics,
        "score": score,
        "promoted_at": datetime.now().isoformat()
    }
    with open(CURRENT_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_champion_score() -> float:
    if not os.path.exists(CURRENT_FILE):
        return -1.0
    try:
        with open(CURRENT_FILE, "r") as f:
            data = json.load(f)
            return data.get("score", 0.0)
    except:
        return -1.0
