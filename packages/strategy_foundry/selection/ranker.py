"""Strategy Ranker"""
from typing import List, Dict, Any

def calculate_score(metrics: Dict[str, Any], walkforward: Dict[str, Any]) -> float:
    """
    Calculate composite score for a strategy based on its metrics and walkforward results.
    
    Args:
        metrics: Dictionary containing strategy metrics (sharpe, max_dd, etc.)
        walkforward: Dictionary containing walk-forward validation results
        
    Returns:
        Composite score (float)
    """
    sharpe = metrics.get("sharpe", 0)
    max_dd = metrics.get("max_dd", 1)  # Lower is better
    
    # Stability bonus from OOS
    stability = walkforward.get("positive_folds", 0) / 5.0  # normalized
    
    score = (sharpe * 0.4) + ((1 - max_dd) * 0.3) + (stability * 0.3)
    return score

def rank_candidates(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank candidates based on composite score.
    Score = Sharpe * 0.4 + (1 - MaxDD) * 0.3 + Stability * 0.3
    """

    scored = []
    for res in results:
        m = res.get("metrics", {})
        if not m:
            continue

        wf = res.get("walkforward", {})
        score = calculate_score(m, wf)

        res["score"] = score
        scored.append(res)

    return sorted(scored, key=lambda x: x["score"], reverse=True)
