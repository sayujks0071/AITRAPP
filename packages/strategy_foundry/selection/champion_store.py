"""Champion Storage"""
import json
from pathlib import Path
from typing import Optional, Dict, Any

CHAMPION_DIR = Path(__file__).parent.parent / "results" / "champions"

class ChampionStore:
    def __init__(self):
        CHAMPION_DIR.mkdir(parents=True, exist_ok=True)

    def load_current(self, symbol: str = "NIFTY") -> Optional[Dict[str, Any]]:
        fname = CHAMPION_DIR / f"current_{symbol}.json"
        if fname.exists():
            with open(fname) as f:
                return json.load(f)
        return None

    def save_new(self, candidate: Dict[str, Any], timestamp: str, symbol: str = "NIFTY"):
        # Save versioned
        fname = f"{timestamp}_{symbol}_{candidate.get('id', 'unknown')}.json"
        with open(CHAMPION_DIR / fname, 'w') as f:
            json.dump(candidate, f, indent=2)

        # Update current
        with open(CHAMPION_DIR / f"current_{symbol}.json", 'w') as f:
            json.dump(candidate, f, indent=2)
