"""Ranker and Champion Selection"""
import pandas as pd
import json
import os
from pathlib import Path

class Ranker:
    def rank(self, results: list, timeframe: str) -> pd.DataFrame:
        df = pd.DataFrame(results)
        if df.empty: return df

        # Calculate Score
        # 25% Sharpe, 25% Calmar, 20% Return, 15% Stability, 15% Other
        # Normalize
        cols = ["sharpe", "calmar", "total_return", "consistency"]
        for c in cols:
            if c not in df.columns: df[c] = 0.0

        df["score"] = (
            0.25 * df["sharpe"] +
            0.25 * df["calmar"] + # Note: Calmar might be inf if DD is 0
            0.20 * df["total_return"] +
            0.15 * df["consistency"]
        )

        df = df.sort_values("score", ascending=False)
        return df

class ChampionStore:
    def __init__(self, path="packages/strategy_foundry/results/champions"):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def save_champion(self, candidate_dict: dict, metrics: dict, timeframe: str):
        data = {
            "candidate": candidate_dict,
            "metrics": metrics,
            "timeframe": timeframe,
            "timestamp": pd.Timestamp.now().isoformat()
        }

        # Save current
        with open(self.path / "current.json", "w") as f:
            json.dump(data, f, indent=2)

        # Save versioned
        fname = f"{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}_{candidate_dict['id']}.json"
        with open(self.path / fname, "w") as f:
            json.dump(data, f, indent=2)

    def load_current(self):
        try:
            with open(self.path / "current.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
