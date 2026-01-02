"""
Evaluation and Selection logic.
"""
import pandas as pd
import numpy as np
from typing import List, Dict
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.backtest.engine import BacktestEngine

class WalkForwardEvaluator:
    def __init__(self, data: pd.DataFrame, n_folds: int = 3, train_ratio: float = 0.7):
        self.data = data
        self.n_folds = n_folds
        self.train_ratio = train_ratio

    def evaluate(self, candidate: StrategyCandidate, engine: BacktestEngine) -> Dict:
        """
        Perform walk-forward evaluation.
        Split data into N folds (expanding window or rolling?).
        Let's use expanding window for stability, or simple K-fold chunks.
        Standard Walk-Forward: Train on Chunk 1, Test on Chunk 2. Train on 1+2, Test 3.

        Returns aggregated OOS metrics.
        """
        # Determine splits
        # We need at least 2 years of data ideally.
        total_days = len(self.data)
        if total_days < 500:
            # Too short for meaningful WF
            return {"status": "skipped", "reason": "insufficient_data"}

        fold_size = total_days // (self.n_folds + 1)

        oos_results = []

        for i in range(self.n_folds):
            # Train: 0 to (i+1)*fold_size
            # Test: (i+1)*fold_size to (i+2)*fold_size

            train_end_idx = (i + 1) * fold_size
            test_end_idx = (i + 2) * fold_size

            # We don't actually "train" (optimize params) here because
            # the candidate comes with fixed params.
            # We just validate performance on OOS chunks.
            # So effectively we are just checking consistency across time chunks.

            test_start_date = self.data.index[train_end_idx]
            test_end_date = self.data.index[min(test_end_idx, len(self.data)-1)]

            res = engine.run(candidate, start_date=test_start_date, end_date=test_end_date)
            res["fold"] = i
            oos_results.append(res)

        return self._aggregate_results(oos_results)

    def _aggregate_results(self, results: List[Dict]) -> Dict:
        # Compute average/median metrics over folds
        metrics = [r["metrics"] for r in results]

        avg_sharpe = np.mean([m["sharpe"] for m in metrics])
        avg_cagr = np.mean([m["cagr"] for m in metrics])
        max_dd = np.max([m["max_dd"] for m in metrics]) # Worst DD seen in any fold

        positive_folds = sum(1 for m in metrics if m["cagr"] > 0)

        # Stability: Dispersion of Sharpe
        sharpes = [m["sharpe"] for m in metrics]
        stability = 1.0 / (np.std(sharpes) + 0.1) # Inverse of std dev

        return {
            "avg_sharpe": avg_sharpe,
            "avg_cagr": avg_cagr,
            "max_dd": max_dd,
            "positive_folds": positive_folds,
            "stability": stability,
            "fold_results": results
        }

class Ranker:
    @staticmethod
    def score(metrics: Dict) -> float:
        """
        Composite score:
        + 30% OOS Sharpe
        + 25% OOS Calmar (using avg CAGR / worst DD)
        + 20% OOS CAGR
        + 15% Stability
        - 10% Turnover (penalty, omitted for now or proxy via trades)
        """
        if metrics.get("max_dd", 1) == 0: calmar = 0
        else: calmar = metrics.get("avg_cagr", 0) / metrics.get("max_dd", 1)

        s = 0.3 * metrics.get("avg_sharpe", 0) + \
            0.25 * calmar + \
            0.2 * metrics.get("avg_cagr", 0) + \
            0.15 * metrics.get("stability", 0)

        return s
