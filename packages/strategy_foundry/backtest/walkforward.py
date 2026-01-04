"""
Walk Forward Evaluation
"""
import pandas as pd
import numpy as np
from typing import List, Dict
from packages.strategy_foundry.backtest.engine import BacktestEngine

class WalkForwardValidator:
    def __init__(self, data: pd.DataFrame, strategy: Dict, cost_config: Dict, folds: int = 4):
        self.data = data
        self.strategy = strategy
        self.cost_config = cost_config
        self.folds = folds

    def run(self) -> Dict:
        """
        Run Walk-Forward Analysis.
        Splits data into K folds (expanding window or rolling).
        Here we use expanding window train, rolling test.
        But simple K-fold (Cross Val style) breaks time series.
        Standard Walk Forward:
        | Train | Test |
                | Train | Test |
                        | Train | Test |

        For simplicity and robustness:
        Split data into Folds+1 chunks.
        Fold 1: Train on Chunk 1, Test on Chunk 2
        Fold 2: Train on Chunk 1+2, Test on Chunk 3
        ...
        """
        n_chunks = self.folds + 1
        chunk_size = len(self.data) // n_chunks

        if chunk_size < 50: # Too small
            return None

        fold_metrics = []
        equity_curves = []

        for i in range(1, n_chunks):
            # Train window: start to i*chunk_size
            train_end = i * chunk_size
            test_end = (i + 1) * chunk_size

            # We don't necessarily need to Run Backtest on Train for ranking,
            # only if we were optimizing parameters.
            # But we can log train performance.
            # The spec requires OOS evaluation.

            test_data = self.data.iloc[train_end:test_end]

            engine = BacktestEngine(test_data, self.strategy, self.cost_config)
            res = engine.run()

            if res and res["metrics"]:
                fold_metrics.append(res["metrics"])
                if res.get("equity_curve"):
                     equity_curves.extend(res["equity_curve"])

        if not fold_metrics:
            return None

        # Aggregate Metrics
        # Average Sharpe, Min MaxDD, etc?
        # Or re-compute global metrics from stitched equity?
        # Let's average the metrics for stability score.

        avg_sharpe = np.mean([m["sharpe"] for m in fold_metrics])
        avg_dd = np.mean([m["max_dd"] for m in fold_metrics])
        avg_profit_factor = np.mean([m["profit_factor"] for m in fold_metrics])

        # Stability: variance of sharpe
        sharpe_std = np.std([m["sharpe"] for m in fold_metrics])
        stability = 1.0 / (1.0 + sharpe_std)

        # Count positive folds
        positive_folds = sum(1 for m in fold_metrics if m["sharpe"] > 0)

        return {
            "sharpe": avg_sharpe,
            "max_dd": avg_dd,
            "profit_factor": avg_profit_factor,
            "stability": stability,
            "positive_folds": positive_folds,
            "total_folds": self.folds,
            "trades": sum(m["trades"] for m in fold_metrics),
            "cagr": np.mean([m["cagr"] for m in fold_metrics]), # Average CAGR of folds
            "win_rate": np.mean([m["win_rate"] for m in fold_metrics]),
            "calmar": np.mean([m["calmar"] for m in fold_metrics])
        }
