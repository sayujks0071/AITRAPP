"""Strategy Ranker"""
from typing import List, Dict, Any

def rank_candidates(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank candidates based on composite score.
    """
    # Score = Sharpe * 0.4 + (1 - MaxDD) * 0.3 + Sortino * 0.2 + Calmar * 0.1
    # Adjust weights as needed.

    scored = []
    for res in results:
        m = res.get("metrics", {})
        if not m:
            continue

        sharpe = m.get("sharpe", 0)
        max_dd = m.get("max_dd", 1) # Lower is better
        sortino = m.get("sortino", 0)
        calmar = m.get("calmar", 0)

        # Stability bonus from OOS
        wf = res.get("walkforward", {})
        stability = wf.get("positive_folds", 0) / 5.0 # normalized

        score = (sharpe * 0.4) + ((1 - max_dd) * 0.3) + (stability * 0.3)

        res["score"] = score
        scored.append(res)

    return sorted(scored, key=lambda x: x["score"], reverse=True)
