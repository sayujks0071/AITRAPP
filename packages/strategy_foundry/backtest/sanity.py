from typing import Dict, Any

def check_sanity(metrics: Dict[str, Any], fast_mode: bool = False) -> Dict[str, Any]:
    """
    Check if strategy passes sanity gates.
    """
    min_trades = 10 if fast_mode else 30
    min_folds = 1 if fast_mode else 2
    max_dd = 0.35

    reasons = []
    passed = True

    if metrics['trades'] < min_trades:
        passed = False
        reasons.append(f"Too few trades: {metrics['trades']} < {min_trades}")

    if metrics['max_dd'] > max_dd:
        passed = False
        reasons.append(f"Max DD too high: {metrics['max_dd']:.2f} > {max_dd}")

    if metrics.get('positive_folds', 0) < min_folds:
        passed = False
        reasons.append(f"Not enough positive folds: {metrics.get('positive_folds')} < {min_folds}")

    return {
        "passed": passed,
        "reasons": reasons
    }
