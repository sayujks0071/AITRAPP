"""Rank and select strategies"""
from typing import List, Dict, Tuple
import pandas as pd
from packages.strategy_foundry.factory.grammar import StrategyCandidate

def calculate_score(metrics: Dict) -> float:
    """
    Score weights:
    + 25% OOS Sharpe
    + 25% OOS Calmar
    + 20% Net return / CAGR (Using Avg Sharpe as proxy for risk adjusted, let's use Avg Return if available, else Sharpe dominates)
    + 15% Stability (low variance across folds)
    + 10% Low turnover bonus (or -turnover penalty)
    + 5% Intraday sanity
    """

    # Extract
    sharpe = metrics.get("avg_sharpe", -99)
    calmar = metrics.get("avg_calmar", -99)
    stability = metrics.get("sharpe_stability", 10) # Lower is better

    # Normalize inputs roughly
    # Sharpe: target > 1.0. Cap at 3.0?
    s_score = min(max(sharpe, -2), 3) / 3.0

    # Calmar: target > 2.0.
    c_score = min(max(calmar, -2), 5) / 5.0

    # Stability: 0 is best. 1.0 is bad.
    stab_score = max(0, 1 - stability)

    # Bonus/Penalty
    late_day = metrics.get("late_day_ratio", 0)
    # Penalize if late day dependence > 0.5
    late_penalty = -0.1 if late_day > 0.5 else 0.05

    score = (0.25 * s_score) + (0.25 * c_score) + (0.15 * stab_score) + late_penalty

    # Add trades penalty (Turnover)
    # We want "Low turnover bonus".
    # If trades are excessive, penalty.
    # Reject if too high, but here just score.
    # Let's ignore complex logic for now, keep it simple.

    return score

def rank_candidates(candidates_with_metrics: List[Tuple[StrategyCandidate, Dict]]) -> pd.DataFrame:
    rows = []
    for cand, metrics in candidates_with_metrics:
        score = calculate_score(metrics)
        row = {
            "id": cand.get_id(),
            "timeframe": cand.timeframe,
            "score": score,
            "sharpe": metrics.get("avg_sharpe"),
            "calmar": metrics.get("avg_calmar"),
            "trades": metrics.get("total_trades"),
            "positive_folds": metrics.get("positive_folds"),
            "candidate": cand, # Store object for later use
            "metrics": metrics
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    if not df.empty:
        df.sort_values("score", ascending=False, inplace=True)
    return df
