import os
import json
import structlog
from typing import Optional
from packages.strategy_foundry.factory.grammar import StrategyCandidate

logger = structlog.get_logger(__name__)

CHAMPION_DIR = "packages/strategy_foundry/results/champions"
CURRENT_CHAMPION_FILE = os.path.join(CHAMPION_DIR, "current.json")

def load_champion() -> Optional[StrategyCandidate]:
    if not os.path.exists(CURRENT_CHAMPION_FILE):
        return None

    try:
        with open(CURRENT_CHAMPION_FILE, "r") as f:
            data = json.load(f)
            return StrategyCandidate(
                id=data["id"],
                grammar=data["grammar"],
                params=data["params"],
                metrics=data.get("metrics", {})
            )
    except Exception as e:
        logger.error("Failed to load champion", error=str(e))
        return None

def save_champion(candidate: StrategyCandidate, timestamp: str):
    os.makedirs(CHAMPION_DIR, exist_ok=True)

    data = {
        "id": candidate.id,
        "grammar": candidate.grammar,
        "params": candidate.params,
        "metrics": candidate.metrics,
        "promoted_at": timestamp
    }

    # Save current
    with open(CURRENT_CHAMPION_FILE, "w") as f:
        json.dump(data, f, indent=2)

    # Save versioned
    version_file = os.path.join(CHAMPION_DIR, f"{timestamp}_{candidate.id}.json")
    with open(version_file, "w") as f:
        json.dump(data, f, indent=2)

    logger.info("Champion promoted", id=candidate.id)
