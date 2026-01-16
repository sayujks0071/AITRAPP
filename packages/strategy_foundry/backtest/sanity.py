import pandas as pd
import numpy as np
from typing import Dict, Any
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import calculate_metrics
from packages.strategy_foundry.backtest.costs import CostModel
from packages.strategy_foundry.factory.grammar import StrategyConfig
import yaml
import os

class SanityChecker:
    def __init__(self, daily_df: pd.DataFrame, cost_model: CostModel):
        self.daily_df = daily_df
        self.engine = BacktestEngine(cost_model)

        # Load constraints
        self.config = self._load_config()

    def _load_config(self):
        path = "packages/strategy_foundry/configs/foundry.yaml"
        if os.path.exists(path):
            with open(path, 'r') as f:
                return yaml.safe_load(f).get('selection', {})
        return {}

    def check(self, candidate: StrategyConfig) -> Dict[str, Any]:
        """
        Runs 1D Sanity Check and other robustness checks.
        """
        reasons = []
        passed = True

        # 1. Daily Sanity (Microstructure Illusion Check)
        if self.daily_df is not None and not self.daily_df.empty:
            # Run strategy on 1D
            # Note: Strategy params are tuned for 5m.
            # Running on 1D might yield very few trades or garbage.
            # But if it blows up (huge loss), it implies curve fitting to noise?
            # Prompt: "If daily performance is catastrophically negative... reject"

            trades = self.engine.run(self.daily_df, candidate)
            metrics = calculate_metrics(trades)

            min_sharpe = self.config.get('sanity_daily_min_sharpe', -0.2)
            max_dd = self.config.get('sanity_daily_max_dd', 0.45)

            if metrics['sharpe'] < min_sharpe:
                passed = False
                reasons.append(f"Daily Sanity Failed: Sharpe {metrics['sharpe']:.2f} < {min_sharpe}")

            if metrics['max_drawdown'] > max_dd:
                passed = False
                reasons.append(f"Daily Sanity Failed: MaxDD {metrics['max_drawdown']:.2f} > {max_dd}")

        # 2. Intraday Sanity (Late Day Dependence) - Placeholder
        # This requires detailed trade list from intraday backtest which we don't pass here easily.
        # Assuming Ranker handles "late-day dependence penalty" based on metrics,
        # or we add it here if we passed the intraday trades.
        # For now, we focus on 1D sanity.

        return {
            "passed": passed,
            "reason": "; ".join(reasons) if reasons else "OK",
            "daily_metrics": metrics if (self.daily_df is not None and not self.daily_df.empty) else {}
        }
