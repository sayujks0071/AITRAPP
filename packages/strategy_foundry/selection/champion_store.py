import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)

class ChampionStore:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.current_file = base_dir / "current.json"
        self.history_dir = base_dir / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def load_champion(self) -> Optional[Dict[str, Any]]:
        if not self.current_file.exists():
            return None
        try:
            with open(self.current_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load champion: {e}")
            return None

    def promote_champion(self, candidate: Dict[str, Any], timestamp: str):
        """
        Promote a new champion.
        candidate: dict with id, params, metrics, score
        """
        # Archive current if exists
        if self.current_file.exists():
            # Generate backup name
            # Try to read ID from it
            old_champ = self.load_champion()
            old_id = old_champ.get('id', 'unknown') if old_champ else 'unknown'
            archive_path = self.history_dir / f"{timestamp}_archived_{old_id}.json"
            shutil.copy(self.current_file, archive_path)

        # Save new
        champion_data = {
            "id": candidate['id'],
            "promoted_at": timestamp,
            "params": candidate['params'],
            "metrics": candidate['metrics'],
            "score": candidate['score'],
            "rule_summary": candidate['rule_summary']
        }

        with open(self.current_file, 'w') as f:
            json.dump(champion_data, f, indent=2)

        # Also save a versioned copy
        version_path = self.history_dir / f"{timestamp}_{candidate['id']}.json"
        with open(version_path, 'w') as f:
            json.dump(champion_data, f, indent=2)

        logger.info(f"Promoted new champion: {candidate['id']}")
