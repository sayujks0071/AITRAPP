"""Backtest Sanity Checks"""
from typing import Dict, List

def check_sanity(metrics: Dict, min_trades=30, max_dd_pct=35.0) -> bool:
    """
    Reject strategies that don't meet basic criteria.
    """
    if not metrics:
        return False

    trades = metrics.get("total_trades", 0)
    dd = metrics.get("max_dd", -1.0) # usually negative e.g. -0.20

    # 1. Trade Count
    if trades < min_trades:
        return False

    # 2. Max Drawdown (dd is negative, so abs(dd) > 0.35 is bad)
    # If dd is -0.40, abs(-0.40)*100 = 40 > 35 -> Fail
    if abs(dd) * 100 > max_dd_pct:
        return False

    return True
