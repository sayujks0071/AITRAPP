"""
Champion Store
Manages persistence of champion strategies.
"""
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

CHAMPIONS_DIR = Path("packages/strategy_foundry/results/champions")

class ChampionStore:
    def __init__(self):
        CHAMPIONS_DIR.mkdir(parents=True, exist_ok=True)
        self.current_file = CHAMPIONS_DIR / "current.json"

    def load_current(self) -> Dict[str, Any]:
        if self.current_file.exists():
            try:
                with open(self.current_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_new_champion(self, strategy_config: Dict, metrics: Dict, timeframe: str, run_ts: str):
        data = {
            "strategy": strategy_config,
            "metrics": metrics,
            "timeframe": timeframe,
            "promoted_at": run_ts
        }

        # Save versioned
        version_file = CHAMPIONS_DIR / f"{run_ts}_{strategy_config['id']}.json"
        with open(version_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Update current
        with open(self.current_file, 'w') as f:
            json.dump(data, f, indent=2)
