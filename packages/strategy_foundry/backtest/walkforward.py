import pandas as pd
from typing import List, Tuple, Dict, Any
from datetime import timedelta
from packages.strategy_foundry.backtest.engine import FastBacktestEngine
from packages.strategy_foundry.factory.generator import GeneratedStrategy
import numpy as np

class WalkForwardEvaluator:
    """
    Implements Walk-Forward Analysis (Expanding Window).
    Train on past, Test on future.
    """

    def __init__(self, n_folds: int = 3, train_ratio: float = 0.7):
        self.n_folds = n_folds
        self.train_ratio = train_ratio

    def split_data(self, df: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Splits data into (In-Sample, Out-of-Sample) folds.
        Expanding window approach.
        """
        n = len(df)
        fold_size = n // (self.n_folds + 1)

        folds = []
        for i in range(1, self.n_folds + 1):
            train_end = fold_size * (i + 1) # Increasing training size
            # Or fixed window? Expanding is safer for stability check.
            # User says: "Walk-Forward Analysis ... Expanding window for training"

            # Simple expanding window:
            # Fold 1: Train [0..K], Test [K..K+M]
            # Fold 2: Train [0..K+M], Test [K+M..K+2M]

            # Let's divide total data into N+1 chunks.
            # Train starts with 1 chunk, tests on next. Then Train 2 chunks, test on next.

            train_idx = int(n * (i / (self.n_folds + 1)))
            test_idx = int(n * ((i + 1) / (self.n_folds + 1)))

            train_data = df.iloc[:train_idx]
            test_data = df.iloc[train_idx:test_idx]

            folds.append((train_data, test_data))

        return folds

    def evaluate(self, strategy: GeneratedStrategy, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Run WFA on strategy.
        Returns aggregated OOS metrics.
        """
        folds = self.split_data(df)
        oos_results = []

        for train_df, test_df in folds:
            # We don't "optimize" here (that's grid search), we just Validate.
            # The "Strategy Self-Generation" creates random candidates.
            # We check if they hold up OOS.

            engine = FastBacktestEngine(test_df)
            res = engine.run(strategy)
            oos_results.append(res)

        # Aggregate Results
        avg_sharpe = np.mean([r["metrics"]["sharpe"] for r in oos_results])
        avg_cagr = np.mean([r["metrics"]["cagr"] for r in oos_results])
        avg_dd = np.mean([r["metrics"]["max_dd"] for r in oos_results])

        positive_folds = sum([1 for r in oos_results if r["metrics"]["sharpe"] > 0])

        stability_score = 1.0 - np.std([r["metrics"]["sharpe"] for r in oos_results])

        return {
            "avg_sharpe": float(avg_sharpe),
            "avg_cagr": float(avg_cagr),
            "avg_max_dd": float(avg_dd),
            "positive_folds": int(positive_folds),
            "stability": float(stability_score),
            "fold_results": [r["metrics"] for r in oos_results]
        }
