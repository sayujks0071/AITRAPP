import os
import json
import structlog
from datetime import datetime
from typing import Dict, Any

logger = structlog.get_logger(__name__)

CHAMPION_DIR = os.path.join(os.path.dirname(__file__), "../results/champions")
CURRENT_CHAMPION_FILE = os.path.join(CHAMPION_DIR, "current.json")

class ChampionStore:
    def __init__(self):
        if not os.path.exists(CHAMPION_DIR):
            os.makedirs(CHAMPION_DIR)

    def get_current_champion(self) -> Dict[str, Any]:
        if os.path.exists(CURRENT_CHAMPION_FILE):
            try:
                with open(CURRENT_CHAMPION_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def promote_new_champion(self, candidate_json: Dict[str, Any], metrics: Dict[str, Any], timestamp: str):
        """
        Save new champion.
        """
        data = {
            "candidate": candidate_json,
            "metrics": metrics,
            "promoted_at": timestamp
        }

        # Save historical version
        fname = f"{timestamp}_{candidate_json['id']}.json"
        with open(os.path.join(CHAMPION_DIR, fname), "w") as f:
            json.dump(data, f, indent=2)

        # Update current
        with open(CURRENT_CHAMPION_FILE, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Promoted new champion: {candidate_json['id']}")
