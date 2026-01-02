import pandas as pd
import numpy as np
from typing import Dict, Any, List
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategySpec

class WalkForwardEvaluator:
    """Walk-forward analysis for strategy evaluation"""

    def __init__(self, data: pd.DataFrame, engine_class=BacktestEngine, folds: int = 4, min_train_pct: float = 0.2):
        self.data = data
        self.engine_class = engine_class
        self.folds = folds
        self.min_train_pct = min_train_pct

    def evaluate(self, strategy: StrategySpec) -> Dict[str, Any]:
        """
        Run walk-forward evaluation.

        Returns:
            Dict containing aggregated OOS metrics and fold details.
        """
        n = len(self.data)
        if n < 500: # Not enough data
            return {"error": "Insufficient data"}

        # Define splits
        # We want 'folds' OOS periods.
        # We reserve 'min_train_pct' for initial training.
        # The rest is split into 'folds' chunks.

        train_end_idx = int(n * self.min_train_pct)
        remaining = n - train_end_idx
        fold_size = int(remaining / self.folds)

        fold_results = []
        equity_curves = []

        for i in range(self.folds):
            start_test = train_end_idx + (i * fold_size)
            end_test = start_test + fold_size
            if i == self.folds - 1:
                end_test = n # Capture remainder

            # Train data: 0 to start_test (Expanding window)
            # Test data: start_test to end_test

            # We only care about OOS performance for ranking.
            # But BacktestEngine runs on provided dataframe.
            # We provide ONLY test data to engine?
            # Problem: Indicators need lookback.
            # Solution: Provide data including lookback period, but only count trades in OOS period.
            # BacktestEngine doesn't support "start_date" param yet.
            # We can slice data with lookback overlap.

            lookback = 200 # Max lookback for indicators
            slice_start = max(0, start_test - lookback)

            test_data = self.data.iloc[slice_start:end_test].copy()

            # Run Engine
            engine = self.engine_class(test_data)
            result = engine.run(strategy)

            # Filter trades to only those starting in OOS period
            # start_test index corresponds to self.data.index[start_test]
            oos_start_dt = self.data.index[start_test]

            oos_trades = [t for t in result["trades"] if t["entry_time"] >= oos_start_dt]

            # Recalculate metrics for OOS trades
            from packages.strategy_foundry.backtest.metrics import calculate_metrics
            oos_metrics = calculate_metrics(oos_trades, engine.initial_capital)

            fold_results.append(oos_metrics)

        # Aggregate Results
        avg_sharpe = np.mean([m["sharpe_ratio"] for m in fold_results])
        avg_calmar = np.mean([m.get("calmar", 0) for m in fold_results]) # metrics might not have calmar yet
        avg_profit_factor = np.mean([m["profit_factor"] for m in fold_results])
        avg_dd = np.mean([m["max_drawdown"] for m in fold_results])

        # Stability: Variance of Sharpe
        sharpe_std = np.std([m["sharpe_ratio"] for m in fold_results])

        return {
            "folds": fold_results,
            "avg_sharpe": float(avg_sharpe),
            "avg_profit_factor": float(avg_profit_factor),
            "avg_max_drawdown": float(avg_dd),
            "sharpe_std": float(sharpe_std),
            "total_trades": sum(m["total_trades"] for m in fold_results)
        }
