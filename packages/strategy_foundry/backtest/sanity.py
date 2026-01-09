"""
Sanity Checks
Sanity checks for strategies to prevent overfitting and ensure robustness.
"""
from typing import Dict, Any, List
import pandas as pd

class SanityChecker:
    @staticmethod
    def check_intraday_sanity(trades: List[Dict[str, Any]], timeframe: str) -> Dict[str, bool]:
        """
        Check for intraday specific issues.
        1. Late day dependence: If > 50% profit comes from last 30 mins
        2. Overtrading: too many trades per day
        """
        if not trades:
            return {"passed": True, "late_day_dependence": False, "overtrading": False}

        df = pd.DataFrame(trades)
        if df.empty:
             return {"passed": True, "late_day_dependence": False, "overtrading": False}

        # 1. Late Day Dependence
        # Check if exit_time is after 15:00
        # Assume 'exit_time' is datetime.
        # We look at profit contribution.
        total_profit = df['pnl'].sum()
        if total_profit > 0:
            late_mask = df['exit_time'].apply(lambda x: x.hour == 15 and x.minute >= 0)
            late_profit = df[late_mask]['pnl'].sum()

            late_ratio = late_profit / total_profit
            if late_ratio > 0.5:
                return {"passed": False, "late_day_dependence": True, "overtrading": False}

        # 2. Overtrading
        # Count trades per day
        df['date'] = df['entry_time'].dt.date
        trades_per_day = df.groupby('date').size()
        avg_trades = trades_per_day.mean()

        # Threshold: > 10 trades/day on average is suspicious for this timeframe?
        # Requirement: "too many trades/day -> penalize"
        # Let's say max 15.
        if avg_trades > 15:
             return {"passed": False, "late_day_dependence": False, "overtrading": True}

        return {"passed": True, "late_day_dependence": False, "overtrading": False}

    @staticmethod
    def check_daily_sanity(daily_metrics: Dict[str, Any]) -> bool:
        """
        Check if daily performance is catastrophically bad.
        """
        if daily_metrics['sharpe'] < -0.2:
            return False
        if daily_metrics['max_drawdown'] > 0.45:
            return False
        return True
