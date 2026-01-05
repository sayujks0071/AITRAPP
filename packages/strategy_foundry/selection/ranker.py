"""
Strategy Foundry - Ranking and Selection.
"""
import pandas as pd
from typing import List, Dict, Any

def score_candidate(metrics: Dict[str, Any]) -> float:
    """
    Compute composite score.
    """
    m = metrics["metrics"]

    sharpe = m.get("sharpe", 0)
    cagr = m.get("cagr", 0)

    # Stability: Standard deviation of Sharpe across folds
    folds = m.get("folds", [])
    fold_sharpes = [f.get("sharpe", 0) for f in folds]
    stability = 1.0 / (pd.Series(fold_sharpes).std() + 0.1)

    # Calmar proxy: avg cagr / avg max dd
    avg_dd = sum([abs(f.get("max_drawdown", 0)) for f in folds]) / len(folds)
    calmar = cagr / avg_dd if avg_dd > 0 else 0

    # Score
    # 30% Sharpe + 25% Calmar + 20% CAGR + 15% Stability - Turnover?

    # Normalize inputs roughly
    # Sharpe target 1.0
    # Calmar target 2.0
    # CAGR target 0.2

    s_score = min(sharpe, 3.0) * 30
    c_score = min(calmar, 5.0) * 5 # scaled down
    r_score = min(cagr, 1.0) * 100 * 0.2
    stab_score = min(stability, 5.0) * 3

    total = s_score + c_score + r_score + stab_score
    return total

def rank_candidates(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank candidates by score.
    """
    for res in results:
        res["score"] = score_candidate(res["metrics"])

    return sorted(results, key=lambda x: x["score"], reverse=True)
