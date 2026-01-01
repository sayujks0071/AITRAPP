"""Champion Store"""
import os
import json
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

CHAMPION_DIR = "packages/strategy_foundry/results/champions"
CURRENT_CHAMPION_FILE = os.path.join(CHAMPION_DIR, "current.json")

class ChampionStore:
    def __init__(self):
        os.makedirs(CHAMPION_DIR, exist_ok=True)

    def load_champion(self) -> Dict[str, Any]:
        if os.path.exists(CURRENT_CHAMPION_FILE):
            try:
                with open(CURRENT_CHAMPION_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load champion: {e}")
        return None

    def save_champion(self, candidate: Dict[str, Any]):
        # Save as current
        with open(CURRENT_CHAMPION_FILE, "w") as f:
            json.dump(candidate, f, indent=2)

        # Save history version
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        hist_path = os.path.join(CHAMPION_DIR, f"champion_{ts}.json")
        with open(hist_path, "w") as f:
            json.dump(candidate, f, indent=2)

        logger.info(f"New champion saved: {candidate.get('id')}")
