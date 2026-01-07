"""
Sanity Checks
"""
from typing import Dict

class SanityChecker:
    @staticmethod
    def check_daily_sanity(metrics: Dict[str, float]) -> bool:
        """
        Check if daily performance is catastrophic.
        """
        # Thresholds from config (hardcoded for now or passed in)
        MIN_SHARPE = -0.2
        MAX_DD = 0.45

        if metrics['sharpe'] < MIN_SHARPE:
            return False

        if metrics['max_drawdown'] > MAX_DD:
            return False

        return True
