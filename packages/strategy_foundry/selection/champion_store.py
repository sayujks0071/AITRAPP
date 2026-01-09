"""
Champion Store
Manages persistence of champion strategies.
"""
import json
import os
from pathlib import Path
from datetime import datetime

CHAMPION_DIR = Path("packages/strategy_foundry/results/champions")

class ChampionStore:
    def __init__(self):
        CHAMPION_DIR.mkdir(parents=True, exist_ok=True)

    def load_current(self) -> dict:
        path = CHAMPION_DIR / "current.json"
        if not path.exists():
            return {}

        with open(path, 'r') as f:
            data = json.load(f)

        metrics = data.get("metrics", {})
        if 'score' not in metrics and 'score' in data:
            metrics['score'] = data['score']
            data['metrics'] = metrics
        elif 'score' not in data and 'score' in metrics:
            data['score'] = metrics['score']

        return data

    def save_new_champion(self, strategy: dict, metrics: dict, timeframe: str, run_ts: str, score: float):
        metrics_with_score = dict(metrics)
        metrics_with_score['score'] = metrics_with_score.get('score', score)

        data = {
            "strategy": strategy,
            "metrics": metrics_with_score,
            "timeframe": timeframe,
            "promoted_at": run_ts,
            "score": score
        }

        version_file = CHAMPION_DIR / f"{run_ts}_{strategy['id']}.json"
        with open(version_file, 'w') as f:
            json.dump(data, f, indent=2)

        with open(CHAMPION_DIR / "current.json", 'w') as f:
            json.dump(data, f, indent=2)
