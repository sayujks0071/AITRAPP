from typing import Dict, Any

def check_sanity(metrics: Dict[str, Any], min_trades: int = 30, max_dd: float = 0.35, min_positive_folds: int = 2) -> bool:
    if not metrics.get("valid", False):
        return False

    agg = metrics["metrics"]
    if agg["trades"] < min_trades:
        return False

    if agg["max_drawdown"] > max_dd:
        return False

    # Check folds
    pos_folds = sum(1 for f in metrics["fold_metrics"] if f["total_return"] > 0)
    if pos_folds < min_positive_folds:
        return False

    return True
