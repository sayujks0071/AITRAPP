"""Sanity Checks"""
from typing import Dict, Any

class SanityChecker:
    @staticmethod
    def check_intraday(metrics: Dict[str, Any], timeframe: str) -> bool:
        """
        Rejection thresholds.
        """
        if timeframe == "5m":
            if metrics["trades"] < 40: return False # Lowered for short run safety
        else:
            if metrics["trades"] < 20: return False

        if metrics["max_dd"] > 0.30: return False
        if metrics["profit_factor"] < 1.05: return False

        return True

    @staticmethod
    def check_daily_sanity(metrics: Dict[str, Any]) -> bool:
        # Catastrophic failure check
        if metrics["max_dd"] > 0.45: return False
        if metrics["sharpe"] < -0.2: return False
        return True
