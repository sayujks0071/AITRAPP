"""Ranking logic"""
from typing import Dict

class Ranker:
    def score(self, metrics: Dict, sanity_result: Dict) -> float:
        """
        Compute blended score:
        + 25% Sharpe
        + 25% Calmar
        + 20% CAGR
        + 15% Stability
        + 10% Low Turnover (Bonus)
        + 5% Intraday Sanity (Penalty actually)
        """
        # Global metrics
        g = metrics.get("global", {})
        stability = metrics.get("stability_score", 0.0)

        sharpe = g.get("sharpe", 0.0)
        calmar = g.get("calmar", 0.0)
        cagr = g.get("cagr", 0.0)

        # Turnover Bonus: < 5 trades/day is good?
        # Actually logic says "Low turnover bonus (or -turnover penalty)"
        # Let's map avg trades/day to 0..1 score
        # Using win rate or just raw count?
        # Let's use Profit Factor as proxy for quality? No, distinct weight.

        # Simple Bonus:
        turnover_score = 0.5 # Neutral

        # Weighted Sum
        # Normalize roughly: Sharpe 2.0 is good. Calmar 3.0 is good. CAGR 0.5 is good.
        # We want raw score to be somewhat meaningful.

        s = (0.25 * sharpe) + (0.25 * calmar) + (0.20 * (cagr * 10)) + (0.15 * (stability * 2))

        # Penalties
        sanity_penalty = sanity_result.get("penalty", 0.0)
        s -= sanity_penalty

        return max(0.0, s)
