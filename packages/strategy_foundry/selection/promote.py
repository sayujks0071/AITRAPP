"""
Strategy Foundry - Champion Store.
"""
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)

CHAMPION_DIR = Path("packages/strategy_foundry/results/champions")
CURRENT_CHAMPION_FILE = CHAMPION_DIR / "current.json"

def load_champion() -> Optional[Dict[str, Any]]:
    if not CURRENT_CHAMPION_FILE.exists():
        return None
    try:
        with open(CURRENT_CHAMPION_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load champion", error=str(e))
        return None

def promote_champion(candidate: Dict[str, Any], reason: str = "New Champion"):
    """
    Promote a candidate to champion.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cid = candidate.get("id", "unknown")

    # Save versioned
    filename = f"{timestamp}_{cid}.json"
    with open(CHAMPION_DIR / filename, 'w') as f:
        json.dump(candidate, f, indent=2)

    # Update current
    with open(CURRENT_CHAMPION_FILE, 'w') as f:
        json.dump(candidate, f, indent=2)

    logger.info("Promoted new champion", id=cid, reason=reason)

def compare_and_promote(best_new_candidate: Dict[str, Any]):
    current = load_champion()

    if not current:
        promote_champion(best_new_candidate, "First Champion")
        return

    # Comparison
    curr_score = current.get("score", 0)
    new_score = best_new_candidate.get("score", 0)

    # Rule: New must exceed current by >= 10%
    if new_score > curr_score * 1.1:
        promote_champion(best_new_candidate, f"Score improvement {curr_score:.2f} -> {new_score:.2f}")
    else:
        logger.info("Champion retained", current_score=curr_score, challenger_score=new_score)
