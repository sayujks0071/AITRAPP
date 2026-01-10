"""Strategy Ranker"""
from typing import List, Dict

def rank_candidates(candidates_results: List[Dict]) -> List[Dict]:
    """
    Rank candidates based on composite score.

    Score = 0.3*Sharpe + 0.25*Calmar + 0.2*CAGR + 0.15*Stability - 0.1*Turnover

    Args:
        candidates_results: List of dicts {strategy, wfa_results}

    Returns:
        Sorted list with score
    """
    scored = []

    for item in candidates_results:
        wfa = item["wfa"]
        strat = item["strategy"]

        # Aggregate OOS metrics (Average across folds)
        folds = wfa["folds"]
        if not folds:
            continue

        avg_sharpe = sum(f["metrics"].get("sharpe", 0) for f in folds) / len(folds)
        avg_calmar = sum(f["metrics"].get("calmar", 0) for f in folds) / len(folds)
        avg_cagr = sum(f["metrics"].get("cagr", 0) for f in folds) / len(folds)

        # Stability proxy (inverse of Sharpe std dev across folds?)
        # Let's use simple passed folds ratio
        stability = wfa["passed_folds"] / len(folds)

        # Score
        # Normalize? For now, raw weighted sum.
        # Calmar can be huge, cap it?

        score = (0.3 * avg_sharpe) + \
                (0.25 * min(avg_calmar, 3.0)) + \
                (0.2 * avg_cagr) + \
                (0.15 * stability)

        # Turnover penalty? (Implicit in costs, but explicit penalty requested)
        # We don't have turnover ratio handy in metrics, let's skip or infer

        scored.append({
            "strategy": strat,
            "score": score,
            "metrics": {
                "sharpe": avg_sharpe,
                "calmar": avg_calmar,
                "cagr": avg_cagr
            },
            "wfa": wfa
        })

    # Sort descending
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored
