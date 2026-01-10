"""Champion Promotion Logic"""
import json
import structlog
from pathlib import Path
from typing import Optional, Dict

logger = structlog.get_logger(__name__)

CHAMPION_DIR = Path(__file__).parent.parent / "results" / "champions"
CHAMPION_DIR.mkdir(parents=True, exist_ok=True)
CURRENT_CHAMPION_FILE = CHAMPION_DIR / "current.json"

def promote_if_better(challenger_score: float, challenger_data: Dict) -> bool:
    """
    Compare challenger with current champion.
    Promote if score >= current + 10% OR MaxDD significantly better.
    """
    if not CURRENT_CHAMPION_FILE.exists():
        _save_champion(challenger_data)
        return True

    try:
        with open(CURRENT_CHAMPION_FILE, "r") as f:
            current = json.load(f)

        current_score = current.get("score", 0.0)

        # Rule 1: Score >= 110% of current
        if challenger_score >= current_score * 1.10:
            logger.info("New champion promoted (Score improvement)",
                       old=current_score, new=challenger_score)
            _save_champion(challenger_data)
            return True

        # Rule 2: MaxDD improvement (requires metrics in data)
        # TODO: Implement if metrics available in saved data

    except Exception as e:
        logger.error("Failed to read current champion", error=str(e))

    return False

def _save_champion(data: Dict):
    # Save current
    with open(CURRENT_CHAMPION_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

    # Save history
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    sid = data.get("strategy", {}).get("id", "unknown")
    hist_file = CHAMPION_DIR / f"{ts}_{sid}.json"
    with open(hist_file, "w") as f:
        json.dump(data, f, indent=2, default=str)

import datetime
