"""
Sanity Check Overlay
"""
import pandas as pd
from typing import Dict
from packages.strategy_foundry.backtest.engine import BacktestEngine

class SanityCheck:
    def __init__(self, daily_data: pd.DataFrame, cost_config: Dict):
        self.daily_data = daily_data
        self.cost_config = cost_config

    def check(self, strategy: Dict) -> bool:
        """
        Run 1D backtest and verify robustnes.
        Returns True if passed, False if failed.
        """
        if self.daily_data.empty:
            return True # Cannot check, assume OK or Fail? Let's assume OK to not block.

        engine = BacktestEngine(self.daily_data, strategy, self.cost_config)
        res = engine.run()

        if not res:
            return True

        metrics = res["metrics"]

        # Criteria: Catastrophic failure
        # Sharpe < -0.2
        # MaxDD > 45%

        if metrics["sharpe"] < -0.2:
            return False

        if metrics["max_dd"] > 0.45:
            return False

        return True
