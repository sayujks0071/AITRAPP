from typing import Dict, Tuple

def check_sanity(metrics: Dict, fast_mode=False) -> Tuple[bool, str]:
    min_trades = 10 if fast_mode else 30

    # Handle missing keys
    trades = metrics.get("trades", 0)
    max_dd = metrics.get("max_dd", -1.0)
    sharpe = metrics.get("sharpe", 0.0)

    if trades < min_trades:
        return False, f"Too few trades ({trades} < {min_trades})"

    if max_dd < -0.35: # -0.35 is -35%
        return False, f"Max DD too high ({max_dd:.1%})"

    if sharpe <= 0:
        return False, "Negative Sharpe"

    return True, "OK"
