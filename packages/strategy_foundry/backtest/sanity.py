"""
Strategy Foundry - Sanity Checks.
"""
from typing import Dict, Any

import os

def check_sanity(metrics: Dict[str, Any], min_trades: int = 30, max_dd: float = 0.35) -> bool:
    """
    Reject strategies that don't meet basic criteria.
    """
    if os.environ.get("FAST_MODE", "0") == "1":
        min_trades = 10
    if not metrics.get("valid", False):
        return False

    m = metrics["metrics"]

    if m["total_trades"] < min_trades:
        return False

    # Check max drawdown in folds?
    # We don't have global max dd easily available from avg, let's check worst fold
    folds = m.get("folds", [])
    if not folds: return False

    worst_dd = min([f.get("max_drawdown", 0) for f in folds]) # max_dd is negative
    if worst_dd < -max_dd:
        return False

    # Positive folds count
    positive_folds = sum(1 for f in folds if f.get("cagr", 0) > 0)
    if positive_folds < (len(folds) / 2):
        return False

    return True
