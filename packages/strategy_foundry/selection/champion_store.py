"""
Champion storage and management.
"""
import json
import shutil
from pathlib import Path
from typing import Optional, Dict
from packages.strategy_foundry.factory.grammar import Strategy

CHAMPION_DIR = Path("packages/strategy_foundry/results/champions")
CURRENT_CHAMPION_FILE = CHAMPION_DIR / "current.json"

class ChampionStore:
    def __init__(self, directory: Path = CHAMPION_DIR):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def load_current_champion(self) -> Optional[Dict]:
        if not CURRENT_CHAMPION_FILE.exists():
            return None
        try:
            with open(CURRENT_CHAMPION_FILE, "r") as f:
                data = json.load(f)
            return data
        except Exception:
            return None

    def save_champion(self, strategy_data: Dict, metrics: Dict, score: float, timestamp: str):
        """
        Save new champion.
        strategy_data: Serialized strategy (ID, params, logic)
        """
        data = {
            "timestamp": timestamp,
            "id": strategy_data["id"],
            "score": score,
            "metrics": metrics,
            "strategy": strategy_data # Should be serializable dict
        }

        # Save versioned
        filename = f"{timestamp}_{strategy_data['id']}.json"
        with open(self.directory / filename, "w") as f:
            json.dump(data, f, indent=2)

        # Update current
        with open(CURRENT_CHAMPION_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def serialize_strategy(self, strategy: Strategy) -> Dict:
        """Helper to serialize strategy object"""
        # We need to reconstruct it later.
        # For now, we store the description strings and params.
        # Ideally we store the structure to rebuild.
        # Given Grammar structure:
        return {
            "id": strategy.id,
            "description": strategy.describe(),
            "entry_rules": [
                {"name": r.name, "params": r.params} for r in strategy.entry_rules
            ],
            "filters": [
                {"name": f.name, "params": f.params} for f in strategy.filters
            ],
            "risk_params": strategy.risk_params
        }
