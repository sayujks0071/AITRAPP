"""
Strategy Ranker and Champion Store
"""
import pandas as pd
import json
import os
import structlog
from datetime import datetime
import yaml

logger = structlog.get_logger(__name__)

class Ranker:
    def __init__(self, config_path="packages/strategy_foundry/configs/foundry.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.weights = self.config['ranking']['weights']

    def score(self, metrics: dict) -> float:
        """
        Calculate weighted score for a candidate.
        Assumes metrics are from OOS testing.
        """
        if not metrics or metrics.get("trades", 0) < 5:
            return -100.0

        # Normalize/Clip metrics to reasonable ranges for scoring
        sharpe = min(max(metrics.get("sharpe", 0), -3), 3)
        calmar = min(max(metrics.get("calmar", 0), -2), 5)
        cagr = min(max(metrics.get("cagr", 0), -0.5), 2)

        # Stability (Placeholder: could be 1 / variance of fold scores)
        # For now assume passed in or default 1
        stability = metrics.get("stability", 0.5)

        # Turnover (Low turnover bonus)
        # Trades per day
        # Assume ideal is 2-5 trades per day. Too high (>20) is bad.
        # metrics['trades'] / days
        # For scoring, we'll just use raw component from logic if pre-computed, else ignore

        score = (
            self.weights['sharpe'] * sharpe +
            self.weights['calmar'] * (calmar / 2) + # Scale down calmar
            self.weights['cagr'] * cagr +
            self.weights['stability'] * stability
        )

        return score

    def rank(self, candidates_results: list) -> pd.DataFrame:
        """
        Rank a list of candidate result dictionaries.
        """
        if not candidates_results:
            return pd.DataFrame()

        df = pd.DataFrame(candidates_results)

        # Calculate Score if not present
        if "score" not in df.columns:
            df["score"] = df["metrics"].apply(self.score)

        # Sort
        df.sort_values("score", ascending=False, inplace=True)
        return df

class ChampionStore:
    def __init__(self, results_dir="packages/strategy_foundry/results"):
        self.champions_dir = os.path.join(results_dir, "champions")
        self.current_file = os.path.join(self.champions_dir, "current.json")
        os.makedirs(self.champions_dir, exist_ok=True)

    def get_current_champion(self):
        if os.path.exists(self.current_file):
            try:
                with open(self.current_file) as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def promote_new_champion(self, candidate, run_ts):
        # Save versioned
        filename = f"{run_ts}_{candidate['id']}.json"
        path = os.path.join(self.champions_dir, filename)
        with open(path, "w") as f:
            json.dump(candidate, f, indent=2)

        # Update current
        with open(self.current_file, "w") as f:
            json.dump(candidate, f, indent=2)

        logger.info(f"Promoted new champion: {candidate['id']}")

    def evaluate_promotion(self, new_best, current_best, config):
        """
        Check if new_best should replace current_best based on rules.
        """
        if not current_best:
            return True

        # Rules
        # Beat blended score by >= 10%
        new_score = new_best.get("score", 0)
        curr_score = current_best.get("score", 0)

        if new_score > curr_score * 1.1:
            return True

        # Or reduce MaxDD by 5% abs (e.g. 0.25 -> 0.20) while similar Sharpe
        new_dd = new_best["metrics"]["max_dd"]
        curr_dd = current_best["metrics"]["max_dd"]

        if (curr_dd - new_dd) >= 0.05 and new_score > curr_score * 0.9:
            return True

        return False
