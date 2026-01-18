import pandas as pd
from typing import Dict, List

def check_sanity(trades_df: pd.DataFrame, timeframe_str: str) -> Dict[str, bool]:
    """
    Returns a dict of sanity checks. True means PASS, False means FAIL/WARNING.
    """
    if trades_df.empty:
        return {"min_trades": False, "late_day_dependence": True, "overtrade": True}

    # 1. Min Trades
    min_trades = 80 if "5m" in timeframe_str else 40
    has_min_trades = len(trades_df) >= min_trades

    # 2. Late Day Dependence
    # Check exits in last 30 mins
    # Assuming 'exit_time' is in trades_df
    trades_df["exit_time"] = pd.to_datetime(trades_df["exit_time"])

    # 15:00 onwards
    late_trades = trades_df[trades_df["exit_time"].dt.time >= pd.to_datetime("15:00").time()]
    late_pnl = late_trades["pnl"].sum()
    total_pnl = trades_df["pnl"].sum()

    if total_pnl > 0 and late_pnl > 0:
        ratio = late_pnl / total_pnl
        not_late_dependent = ratio < 0.5
    else:
        not_late_dependent = True

    # 3. Overtrade
    # Group by date
    trades_per_day = trades_df.groupby(trades_df["exit_time"].dt.date).size()
    avg_trades = trades_per_day.mean()
    not_overtrading = avg_trades < 10 # 10 trades per day is a lot for directional

    return {
        "min_trades": has_min_trades,
        "late_day_dependence": not_late_dependent,
        "overtrade": not_overtrading
    }
