"""Sanity Checks"""
from typing import Dict, Any

def check_sanity(metrics: Dict[str, Any], fast_mode: bool = False) -> tuple[bool, str]:
    """
    Returns (Pass/Fail, Reason)
    """
    min_trades = 10 if fast_mode else 30
    max_dd = 0.35 # 35%

    if not metrics:
        return False, "No metrics"

    if metrics.get('trades', 0) < min_trades:
        return False, f"Too few trades ({metrics.get('trades', 0)} < {min_trades})"

    if abs(metrics.get('max_drawdown', 0)) > max_dd:
         return False, f"Max DD too high ({metrics.get('max_drawdown', 0):.2%} > {max_dd:.0%})"

    return True, "OK"
