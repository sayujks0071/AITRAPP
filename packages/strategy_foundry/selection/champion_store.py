"""
Champion Store
Manages persistence of champion strategies.
"""
import json
import os
from pathlib import Path
from datetime import datetime
from packages.strategy_foundry.factory.grammar import StrategyConfig

CHAMPION_DIR = Path("packages/strategy_foundry/results/champions")

class ChampionStore:
    def __init__(self):
        CHAMPION_DIR.mkdir(parents=True, exist_ok=True)

    def load_current(self) -> dict:
        path = CHAMPION_DIR / "current.json"
        if path.exists():
            with open(path, 'r') as f:
                return json.load(f)
        return {}

    def save_new_champion(self, strategy: dict, metrics: dict, timeframe: str, run_ts: str):
        # Save historical version
        version_file = CHAMPION_DIR / f"{run_ts}_{strategy['id']}.json"
        data = {
            "strategy": strategy,
            "metrics": metrics,
            "timeframe": timeframe,
            "promoted_at": run_ts
        }
        with open(version_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Update current
        with open(CHAMPION_DIR / "current.json", 'w') as f:
            json.dump(data, f, indent=2)
