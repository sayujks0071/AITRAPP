import os
import json
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)

CHAMPION_DIR = os.path.join(os.path.dirname(__file__), "../results/champions")
os.makedirs(CHAMPION_DIR, exist_ok=True)
CURRENT_CHAMPION_FILE = os.path.join(CHAMPION_DIR, "current.json")

def load_champion() -> dict:
    if os.path.exists(CURRENT_CHAMPION_FILE):
        with open(CURRENT_CHAMPION_FILE, "r") as f:
            return json.load(f)
    return None

def save_champion(candidate: dict, reason: str):
    candidate['promoted_at'] = datetime.now().isoformat()
    candidate['promotion_reason'] = reason

    # Versioned
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{timestamp}_{candidate['id']}.json"
    with open(os.path.join(CHAMPION_DIR, fname), "w") as f:
        json.dump(candidate, f, indent=2)

    # Current
    with open(CURRENT_CHAMPION_FILE, "w") as f:
        json.dump(candidate, f, indent=2)

    logger.info("New champion promoted", id=candidate['id'], reason=reason)
