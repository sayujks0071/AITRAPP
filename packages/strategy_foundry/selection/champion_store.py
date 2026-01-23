# StrategyFoundry Implementation
# Strategy Foundry
import json
import structlog
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

logger = structlog.get_logger(__name__)

class ChampionStore:
    """
    Manages persistence of champion strategies.
    """

    def __init__(self, base_dir: str = "packages/strategy_foundry/results/champions"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def load_champion(self, instrument: str) -> Optional[Dict]:
        filepath = self.base_dir / f"champion_{instrument}.json"
        if filepath.exists():
            try:
                with open(filepath, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load champion for {instrument}: {e}")
        return None

    def save_champion(self, instrument: str, candidate: Dict, metrics: Dict, run_id: str):
        data = {
            "instrument": instrument,
            "strategy": candidate, # Spec
            "metrics": metrics,
            "promoted_at": datetime.now().isoformat(),
            "run_id": run_id
        }

        # Save current
        filepath = self.base_dir / f"champion_{instrument}.json"
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        # Save history
        history_path = self.base_dir / f"{run_id}_{instrument}.json"
        with open(history_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Promoted new champion for {instrument}")
