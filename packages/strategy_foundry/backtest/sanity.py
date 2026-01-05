"""
Sanity Checks
Sanity checks for strategies to prevent overfitting and ensure robustness.
"""
from typing import Dict, Any, List

class SanityChecker:
    @staticmethod
    def check_intraday_sanity(trades: List[Dict[str, Any]], timeframe: str) -> Dict[str, bool]:
        """
        Check for intraday specific issues.
        1. Late day dependence: If > 50% profit comes from last 30 mins
        2. Overtrading: too many trades per day
        """
        # Placeholder
        return {"passed": True}

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
