"""Backtest Sanity Checks"""
import pandas as pd
from typing import Dict, Any

def sanity_check_candidate(metrics: Dict[str, Any], fast_mode: bool = False) -> bool:
    # 1. Trade Count
    min_trades = 10 if fast_mode else 30
    if metrics["total_trades"] < min_trades:
        return False

    # 2. Max DD
    if metrics["max_drawdown"] > 0.35: # 35%
        return False

    # 3. Profit Factor
    if metrics["profit_factor"] < 1.05:
        return False

    return True

def daily_sanity_overlay(engine_cls, candidate, daily_data: pd.DataFrame) -> bool:
    """Run candidate on Daily data to check for catastrophic failure"""
    if daily_data.empty: return True # Cannot check

    eng = engine_cls(daily_data)
    res = eng.run(candidate)

    # If daily performance is terrible, reject
    if res["sharpe"] < -0.5: return False
    if res["max_drawdown"] > 0.45: return False

    return True
