"""Backtest Sanity Checks"""
from typing import Dict, Any

def check_sanity(metrics: Dict[str, Any], constraints: Dict[str, Any]) -> bool:
    """
    Return True if passes sanity checks.
    """
    if not metrics:
        return False

    if metrics.get("total_trades", 0) < constraints.get("min_trades", 30):
        return False

    if metrics.get("max_dd", 1.0) > constraints.get("max_drawdown_pct", 35.0) / 100.0:
        return False

    # Additional checks can go here

    return True
