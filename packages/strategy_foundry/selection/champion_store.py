import json
import structlog
from pathlib import Path
from typing import Dict, Any, Optional

logger = structlog.get_logger(__name__)

CHAMPION_DIR = Path("packages/strategy_foundry/results/champions")
CHAMPION_DIR.mkdir(parents=True, exist_ok=True)

class ChampionStore:
    def load_current_champion(self, symbol: str) -> Optional[Dict[str, Any]]:
        path = CHAMPION_DIR / f"current_{symbol}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load champion", symbol=symbol, error=str(e))
            return None

    def save_champion(self, symbol: str, strategy_dict: Dict[str, Any], score: float, metrics: Dict[str, Any]):
        data = {
            "symbol": symbol,
            "strategy": strategy_dict,
            "score": score,
            "metrics": metrics,
            "timestamp": str(pd.Timestamp.now())
        }

        # Save current
        path = CHAMPION_DIR / f"current_{symbol}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        # Save versioned
        vid = strategy_dict.get("id", "unknown")
        ts = pd.Timestamp.now().strftime("%Y%m%d%H%M")
        vpath = CHAMPION_DIR / f"{ts}_{symbol}_{vid}.json"
        with open(vpath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info("Champion saved", symbol=symbol, id=vid, score=score)

import pandas as pd
