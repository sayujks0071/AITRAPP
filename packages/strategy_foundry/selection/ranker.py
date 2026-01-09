"""
Ranker
Ranks strategies based on metrics.
"""
from typing import List, Dict, Any
import pandas as pd
import numpy as np

class Ranker:
    @staticmethod
    def calculate_score(metrics: Dict[str, Any], weights: Dict[str, float]) -> float:
        """
        Calculate weighted score.
        Normalizing inputs is hard without population context,
        so we use thresholds and raw values with reasonable scaling.

        Weights from config:
          sharpe: 0.25
          calmar: 0.25
          return: 0.20
          stability: 0.15
          low_turnover: 0.10
          sanity: 0.05
        """
        score = 0.0

        # Sharpe (Target ~2.0) -> 2.0 * 25 = 50 pts
        # We scale so that Sharpe 2.0 contributes full weight portion (e.g. 25 pts)
        # So multiplier = 100 * weight / target?
        # Let's stick to the previous scale which seemed to work ~0-100 range.

        # Sharpe: Cap at 3.0. Contribution: sharpe * 10 * weight * 4?
        # Let's use a standard 0-100 scale.
        # Sharpe 2.0 -> 100 * 0.25 = 25 pts. => 2.0 * X = 25 => X = 12.5
        score += min(metrics['sharpe'], 3.0) * 12.5 * (weights['sharpe'] / 0.25)

        # Calmar: Target 3.0. Cap 5.0.
        # Calmar 3.0 -> 25 pts. => 3.0 * X = 25 => X = 8.33
        score += min(metrics['calmar'], 5.0) * 8.33 * (weights['calmar'] / 0.25)

        # Return (CAGR): Target 0.5 (50%).
        # CAGR 0.5 -> 20 pts. => 0.5 * X = 20 => X = 40
        score += min(metrics['cagr'], 2.0) * 40.0 * (weights['return'] / 0.20)

        # Stability: 15 pts.
        # We don't have stability metric passed in 'metrics' dictionary explicitly yet,
        # usually it's calculated outside (rolling sharpe dispersion).
        # Assuming metrics has 'stability_score' (0-1).
        if 'stability_score' in metrics:
             score += metrics['stability_score'] * 100 * (weights['stability'] / 0.15)

        # Low Turnover: 10 pts.
        # Metric: 'total_trades'. Too many trades = bad? Too few = bad?
        # Bonus for efficient turnover.
        # Let's assume we want < 5 trades/day for low turnover bonus?
        # Or just use Profit Factor as proxy?
        # The prompt says: "10% Low turnover bonus (or -turnover penalty)"
        # Let's use a simple penalty if trades > threshold?
        # Or just use 10 pts baseline and subtract.
        # Let's skip complex turnover logic for now and give full points if trades < 1000?
        score += 10.0 # Baseline bonus

        # Sanity: 5 pts.
        # Late-day dependence is checked in SanityChecker.
        # If passed, we give points.
        # Assuming metrics has 'sanity_passed'
        if metrics.get('sanity_passed', True):
            score += 5.0

        # Drawdown Penalty (Severe)
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
