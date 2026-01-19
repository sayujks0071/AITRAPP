"""
Promotion logic.
"""
from typing import Dict

def should_promote(new_candidate: Dict, current_champion: Dict = None) -> bool:
    """
    Decide if new candidate should replace current champion.
    new_candidate: dict with 'score', 'metrics'
    current_champion: dict loaded from store
    """
    if current_champion is None:
        return True

    new_score = new_candidate["score"]
    curr_score = current_champion["score"]

    # "Promotion rule: new must exceed current score by >=10%"
    if new_score >= curr_score * 1.10:
        return True

    # "OR lower MaxDD materially."
    # Let's say Materially = 20% better relative improvement?
    # MaxDD is negative number usually in metrics (e.g. -0.20).
    # We store it as such.

    new_dd = new_candidate["metrics"].get("full_metrics", {}).get("max_drawdown", -1.0)
    curr_dd = current_champion["metrics"].get("full_metrics", {}).get("max_drawdown", -1.0)

    # Lower MaxDD means "closer to 0" (less negative).
    # E.g. New -0.10, Old -0.20. New is better.
    # Logic: New > Old * (0.8)? (Since negative)
    # Actually, compare magnitudes.

    if abs(new_dd) < abs(curr_dd) * 0.8: # 20% reduction in drawdown depth
        return True

    return False

def is_live_eligible(metrics: Dict) -> bool:
    """
    Live-eligible gate:
    - OOS Sharpe >= 1.0
    - MaxDD <= 25% (i.e. >= -0.25)
    - >= 3 positive OOS folds (FAST_MODE doesn’t promote... wait, FAST_MODE logic handled in runner)
    """
    sharpe = metrics.get("avg_oos_sharpe", 0)
    max_dd = metrics.get("full_metrics", {}).get("max_drawdown", -1.0)

    # Check folds
    # We need the list of folds
    folds = metrics.get("folds", [])
    positive_folds = sum(1 for m in folds if m.get("total_return", 0) > 0)

    if sharpe >= 1.0 and abs(max_dd) <= 0.25 and positive_folds >= 3:
        return True

    return False
