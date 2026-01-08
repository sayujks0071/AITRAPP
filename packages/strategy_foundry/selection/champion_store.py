"""
Champion Persistence.
"""
import os
import json
import structlog
from packages.strategy_foundry.factory.grammar import StrategyConfig

logger = structlog.get_logger(__name__)

CHAMP_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "champions")

class ChampionStore:
    def __init__(self):
        os.makedirs(CHAMP_DIR, exist_ok=True)
        self.current_path = os.path.join(CHAMP_DIR, "current.json")

    def load_champion(self) -> dict:
        if not os.path.exists(self.current_path):
            return None
        try:
            with open(self.current_path, "r") as f:
                data = json.load(f)
                # Ensure we can reconstruct config
                data["candidate"] = StrategyConfig.from_json(data["candidate_json"])
                return data
        except Exception as e:
            logger.error("Failed to load champion", error=str(e))
            return None

    def save_champion(self, champion_data: dict):
        """
        Save champion.
        champion_data: {
            "candidate": StrategyConfig object,
            "metrics": dict,
            "score": float,
            "instrument": str,
            "timeframe": str
        }
        """
        # Serialize candidate
        data = champion_data.copy()
        data["candidate_json"] = data["candidate"].to_json()
        del data["candidate"] # Remove object

        # Save current
        with open(self.current_path, "w") as f:
            json.dump(data, f, indent=2)

        # Versioned
        ts = int(os.path.getmtime(self.current_path)) if os.path.exists(self.current_path) else 0 # Use file time or now
        # Actually better to use ID
        cid = champion_data["candidate"].id
        v_path = os.path.join(CHAMP_DIR, f"{cid}.json")
        with open(v_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info("Champion saved", id=cid)
