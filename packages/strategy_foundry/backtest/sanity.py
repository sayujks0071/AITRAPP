from typing import Dict, Any

def sanity_check(metrics: Dict[str, Any], fast_mode: bool = False) -> bool:
    """
    Apply sanity checks to reject bad strategies.
    """
    min_trades = 10 if fast_mode else 30
    max_dd = -0.35
    min_pos_folds = 1 if fast_mode else 2

    if metrics["total_trades"] < min_trades:
        return False

    if metrics["full_metrics"]["max_drawdown"] < max_dd: # max_dd is negative
        return False

    if metrics["positive_folds"] < min_pos_folds:
        return False

    # Check if Sharpe is decent (e.g. > 0.5)
    if metrics["full_metrics"]["sharpe"] < 0.5:
        return False

    return True
