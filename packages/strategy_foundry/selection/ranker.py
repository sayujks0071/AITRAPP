"""
Ranker
Ranks strategies based on metrics.
"""
from typing import List, Dict, Any
import pandas as pd

class Ranker:
    @staticmethod
    def calculate_score(metrics: Dict[str, Any], weights: Dict[str, float]) -> float:
        """
        Calculate weighted score.
        Normalizing inputs is hard without population context,
        so we use thresholds and raw values with reasonable scaling.
        """
        score = 0.0

        # Sharpe (Target ~2.0) -> 2.0 * 25 = 50 pts
        score += min(metrics['sharpe'], 3.0) * weights['sharpe'] * 20

        # Calmar (Target ~3.0) -> 3.0 * 25 = 75 pts
        score += min(metrics['calmar'], 5.0) * weights['calmar'] * 15

        # Return (CAGR) -> 0.5 (50%) * 20 = 10 pts
        score += min(metrics['cagr'], 2.0) * weights['return'] * 100

        # Drawdown Penalty
        # If DD > 20%, penalize heavily
        if metrics['max_drawdown'] > 0.2:
            score -= (metrics['max_drawdown'] - 0.2) * 200

        return score

    @staticmethod
    def rank(results: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Rank results.
        results: List of dicts with 'metrics', 'config', 'id'
        """
        df = pd.DataFrame(results)
        if df.empty:
            return df

        # Sort by score descending
        df = df.sort_values('score', ascending=False)
        return df
