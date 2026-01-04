import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)

CHAMPION_DIR = Path("packages/strategy_foundry/results/champions")
CHAMPION_DIR.mkdir(parents=True, exist_ok=True)

def load_current_champion(symbol: str) -> Optional[Dict[str, Any]]:
    path = CHAMPION_DIR / f"current_{symbol}.json"
    if path.exists():
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load champion", error=str(e))
    return None

def save_champion(champion: Dict[str, Any], symbol: str):
    # Save current
    path = CHAMPION_DIR / f"current_{symbol}.json"
    with open(path, "w") as f:
        json.dump(champion, f, indent=2)

    # Versioned
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    v_path = CHAMPION_DIR / f"{ts}_{symbol}_{champion['id']}.json"
    with open(v_path, "w") as f:
        json.dump(champion, f, indent=2)

def promote_if_better(candidate: Dict[str, Any], symbol: str) -> bool:
    current = load_current_champion(symbol)

    if not current:
        save_champion(candidate, symbol)
        logger.info("New champion promoted (first)", symbol=symbol, id=candidate["id"], score=candidate["score"])
        return True

    # Promotion Logic
    # New score >= Current score * 1.10 OR MaxDD significantly better

    score_improvement = candidate["score"] >= current["score"] * 1.10

    curr_dd = current["metrics"]["worst_drawdown"]
    cand_dd = candidate["metrics"]["worst_drawdown"]
    # dd is negative, so closer to 0 is better. -0.10 > -0.20
    dd_improvement = cand_dd > (curr_dd * 0.75) and candidate["score"] >= current["score"] # Less drawdown and at least same score

    if score_improvement or dd_improvement:
        save_champion(candidate, symbol)
        logger.info("New champion promoted", symbol=symbol, id=candidate["id"], score=candidate["score"], prev_score=current["score"])
        return True

    return False
