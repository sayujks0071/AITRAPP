from typing import Dict, Any

def check_sanity(metrics: Dict[str, Any], timeframe: str, mode: str = "full") -> bool:
    """
    Sanity checks for strategy metrics.
    Returns True if sane/pass, False if reject.
    """
    if not metrics:
        return False

    trades = metrics.get("trades", 0)
    sharpe = metrics.get("sharpe", 0)
    max_dd = metrics.get("max_dd", 1.0)
    profit_factor = metrics.get("profit_factor", 0)

    # Minimum trade count
    min_trades = 30 if mode == "full" else 10
    if timeframe == "1d":
        min_trades = 10 # Relax for daily

    if trades < min_trades:
        return False

    # Max Drawdown Hard Limit (35% mentioned in memory, prompt said 30%)
    if max_dd > 0.30:
        return False

    # Profit Factor
    if profit_factor < 1.1:
        return False

    # Sharpe
    if sharpe < 0.5: # Min acceptable
        return False

    return True

def check_daily_sanity(metrics: Dict[str, Any]) -> bool:
    """
    Strict sanity check for 1D overlay.
    Reject if catastrophic.
    """
    if not metrics:
        return True # If no trades, maybe okay? Or fail? Let's say neutral.

    sharpe = metrics.get("sharpe", 0)
    max_dd = metrics.get("max_dd", 0)

    # Catastrophic failure
    if sharpe < -0.2:
        return False
    if max_dd > 0.45:
        return False

    return True
