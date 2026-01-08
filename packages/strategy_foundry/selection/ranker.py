"""
Strategy Ranker.
Computes composite score and ranks candidates.
"""
import pandas as pd
from typing import List, Dict, Any

def score_strategy(metrics: Dict[str, float], stability: float, penalty_turnover: bool = True) -> float:
    """
    Compute Composite Score.
    + 30% Sharpe
    + 25% Calmar
    + 20% CAGR
    + 15% Stability
    - 10% Turnover (Penalty)
    """
    # Normalize inputs?
    # Hard to normalize without population stats.
    # We will use raw values but capped/scaled roughly.

    sharpe = max(0, metrics.get("sharpe", 0)) # Cap at 0 floor
    calmar = max(0, metrics.get("calmar", 0))
    cagr = max(0, metrics.get("cagr", 0) * 100) # Percentage

    # Stability is 1/(std_dev + 0.1). High is good.
    # If std_dev is 0 (perfect), score is 10. If 1, score 1.
    stab = stability

    # Turnover penalty
    # Proxy: trades count or turnover?
    # Use total trades count as proxy for now.
    trades = metrics.get("total_trades", 0)
    # Penalize excessive trading? Or too few?
    # Let's say penalty if > 1000 or < 50
    # Requirement: "10% Turnover penalty"
    # Let's assume turnover reduces score.
    # Higher trades -> Higher penalty.
    turnover_score = min(trades, 500) / 500.0 # 0 to 1

    # Weights
    # Sharpe usually 0-2.
    # Calmar usually 0-2.
    # CAGR usually 0-30.
    # We need to scale them to be comparable.

    s_score = sharpe * 10 # 0-20
    c_score = calmar * 10 # 0-20
    g_score = cagr      # 0-30
    st_score = stab * 2 # 0-20

    score = (0.30 * s_score) + (0.25 * c_score) + (0.20 * g_score) + (0.15 * st_score)
    if penalty_turnover:
        score -= (0.10 * turnover_score * 10) # Subtract 0-1

    return score

def rank_candidates(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank processed candidates.
    """
    ranked = []
    for r in results:
        if not r.get("valid"):
            continue

        m = r["metrics"]
        stability = r["stability_score"]
        score = score_strategy(m, stability)

        r["score"] = score
        ranked.append(r)

    # Sort descending
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked
