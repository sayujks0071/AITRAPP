"""Walk Forward Analysis"""
import pandas as pd
from typing import List, Dict, Any, Tuple
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
        fold_size = total_len // (self.folds + 1)

        oos_metrics_list = []
        equity_curves = []

        for i in range(self.folds):
            # Define OOS window
            # Simple approach: Fixed expanding window or Rolling?
            # Let's do Rolling 80/20 splits roughly.
            # Start: i * fold_size
            # Train End: (i+1) * fold_size + buffer
            # Test Start: Train End
            # Test End: Test Start + fold_size

            # Simpler: Just divide into Folds and treat each as OOS for stability check?
            # But we need "Train" if we were tuning.
            # Here we just check performance on different periods.

            start_idx = i * fold_size
            end_idx = start_idx + fold_size * 2 # 2 chunks size window?

            # Let's just slice the DF and run engine
            # Test Segment
            test_start = (i + 1) * fold_size
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
