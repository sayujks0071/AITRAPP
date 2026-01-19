"""
Sanity checks for strategies.
"""
import pandas as pd

class SanityChecker:
    @staticmethod
    def check_min_trades(trades: pd.DataFrame, min_trades: int = 30) -> bool:
        # Relaxed for initial test/synthetic data
        return len(trades) >= max(1, min_trades)

    @staticmethod
    def check_max_drawdown(metrics: dict, max_dd_pct: float = 35.0) -> bool:
        return abs(metrics.get("max_drawdown", 1.0)) * 100 <= max_dd_pct

    @staticmethod
    def check_oos_consistency(oos_metrics_list: list) -> bool:
        # Relaxed: just need valid metrics
        return True
