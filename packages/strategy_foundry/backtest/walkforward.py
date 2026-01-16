"""Walk-Forward Evaluation"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from .engine import BacktestEngine
from ..factory.generator import StrategyCandidate

class WalkForwardEvaluator:
    def __init__(self, folds: int = 3):
        self.folds = folds
        self.engine = BacktestEngine() # Default config

    def evaluate(self, df: pd.DataFrame, strategy: StrategyCandidate) -> Dict[str, Any]:
        """
        Performs Walk-Forward Validation.
        Returns aggregated OOS metrics.
        """
        # Split data into k folds
        n = len(df)
        fold_size = n // (self.folds + 1)

        oos_metrics = []
        equity_curves = []

        # We use an expanding window or sliding window?
        # Standard WF: Train on [0, k], Test on [k, k+1]
        # Here we just run backtest on OOS segments to verify stability.
        # We don't "optimize" parameters on In-Sample (IS) because our candidates are fixed.
        # So this is strictly OOS cross-validation to see if it holds up in different regimes.

        for i in range(1, self.folds + 1):
            # OOS Segment
            start_idx = i * fold_size
            end_idx = (i + 1) * fold_size if i < self.folds else n

            oos_df = df.iloc[start_idx:end_idx]

            if len(oos_df) < 50: continue # Skip tiny folds

            res = self.engine.run(oos_df, strategy)
            m = res['metrics']
            if m:
                oos_metrics.append(m)
                equity_curves.append(res['equity'])

        # Aggregate Results
        if not oos_metrics:
            return {}

        avg_sharpe = np.mean([m['sharpe'] for m in oos_metrics])
        avg_cagr = np.mean([m['cagr'] for m in oos_metrics])
        avg_dd = np.mean([m['max_drawdown'] for m in oos_metrics])

        # Count positive folds
        positive_folds = sum(1 for m in oos_metrics if m['total_return'] > 0)

        return {
            "oos_sharpe": float(avg_sharpe),
            "oos_cagr": float(avg_cagr),
            "oos_max_dd": float(avg_dd),
            "positive_folds": int(positive_folds),
            "total_folds": len(oos_metrics),
            "fold_metrics": oos_metrics
        }
