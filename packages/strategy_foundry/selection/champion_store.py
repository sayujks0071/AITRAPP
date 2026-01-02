import json
import structlog
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = structlog.get_logger(__name__)

class ChampionStore:
    """Manages storage and retrieval of champion strategies"""

    def __init__(self, data_dir: str = "packages/strategy_foundry/results/champions"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save_champion(self, candidate: Dict[str, Any], timeframe: str) -> None:
        """
        Save the champion strategy.
        Args:
            candidate: Strategy dict (spec + metrics + score)
            timeframe: 5m, 15m, or blended
        """
        try:
            # Add timestamp
            candidate["promoted_at"] = datetime.now().isoformat()

            # Save current
            current_file = self.data_dir / f"current_{timeframe}.json"
            with open(current_file, "w") as f:
                json.dump(candidate, f, indent=2, default=str)

            # Save history
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            hist_file = self.data_dir / f"champion_{timeframe}_{ts}.json"
            with open(hist_file, "w") as f:
                json.dump(candidate, f, indent=2, default=str)

            logger.info(f"Saved champion for {timeframe}", id=candidate.get("id"), score=candidate.get("score"))

        except Exception as e:
            logger.error("Failed to save champion", error=str(e))

    def load_champion(self, timeframe: str) -> Optional[Dict[str, Any]]:
        """Load the current champion for the timeframe"""
        current_file = self.data_dir / f"current_{timeframe}.json"
        if not current_file.exists():
            return None

        try:
            with open(current_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load champion", error=str(e))
            return None
