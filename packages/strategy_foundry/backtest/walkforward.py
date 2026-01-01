"""Walk Forward Analysis"""
import pandas as pd
from typing import Dict, Any
from packages.strategy_foundry.backtest.engine import BacktestEngine

class WalkForwardValidator:
    def __init__(self, engine: BacktestEngine, folds: int = 5):
        self.engine = engine
        self.folds = folds

    def validate(self, strategy_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run Walk-Forward Validation.
        Split data into N folds.
        Since we don't optimize parameters (we just evaluate candidates),
        we treat this as K-Fold Cross Validation or Rolling OOS.

        Rolling Window:
        Train (N years) -> Test (1 year)
        Shift 1 year.

        Actually, prompt says: "Split history into multiple rolling windows... Optimize parameters ONLY on train portion... otherwise treat sampled params as fixed and just evaluate."

        Since we generate random fixed params, we just evaluate on the OOS portions of the folds to verify stability.

        We will return the aggregated OOS metrics.
        """
        df = self.engine.df
        total_len = len(df)
        # Divide data into `self.folds` contiguous segments
        fold_size = total_len // self.folds if self.folds > 0 else total_len

        oos_metrics_list = []

        for i in range(self.folds):
            # Define OOS window as contiguous folds over the full dataset.
            # Each fold uses a non-overlapping test segment:
            #   Fold i: [i * fold_size, (i + 1) * fold_size)
            # The last fold is extended to the end of the dataset to include any remainder.

            # Test Segment
            test_start = i * fold_size
            if test_start >= total_len:
                break

            if i == self.folds - 1:
                # Last fold: include all remaining data
                test_end = total_len
            else:
                test_end = test_start + fold_size

            if test_end > total_len:
                test_end = total_len

            test_df = df.iloc[test_start:test_end]

            # Create sub-engine
            sub_engine = BacktestEngine(test_df, self.engine.initial_capital, self.engine.costs_pct * 10000, self.engine.slippage_pct * 10000)
            res = sub_engine.run(strategy_spec)

            oos_metrics_list.append(res["metrics"])

        # Aggregate
        avg_sharpe = pd.Series([m.get("sharpe", 0) for m in oos_metrics_list]).mean()
        avg_max_dd = pd.Series([m.get("max_dd", 0) for m in oos_metrics_list]).mean()
        positive_folds = sum([1 for m in oos_metrics_list if m.get("total_return", 0) > 0])

        return {
            "avg_sharpe": float(avg_sharpe),
            "avg_max_dd": float(avg_max_dd),
            "positive_folds": positive_folds,
            "fold_metrics": oos_metrics_list
        }
