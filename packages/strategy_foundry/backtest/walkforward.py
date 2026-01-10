"""Walk-Forward Analysis"""
import pandas as pd
from typing import List, Dict, Callable
import structlog

logger = structlog.get_logger(__name__)

class WalkForwardValidator:
    """
    Performs Walk-Forward Validation.
    Splits data into K folds (Train/Test).
    """

    def __init__(self, n_folds=3, train_ratio=0.7):
        self.n_folds = n_folds
        self.train_ratio = train_ratio

    def validate(self, df: pd.DataFrame, strategy, engine_run_fn: Callable) -> Dict:
        """
        Run WFA.

        Args:
            df: Full history
            strategy: Strategy configuration
            engine_run_fn: Function(df, strategy) -> results

        Returns:
            Dict with 'folds' and 'aggregate_score'
        """
        # Split data into folds (Expanding Window)
        # Fold 1: Train [0..T1], Test [T1..T2]
        # Fold 2: Train [0..T2], Test [T2..T3]
        # ...

        n = len(df)
        fold_size = n // (self.n_folds + 1)

        results = []

        for i in range(1, self.n_folds + 1):
            train_end_idx = i * fold_size
            test_end_idx = (i + 1) * fold_size

            # Expanding train
            # train_df = df.iloc[:train_end_idx]
            # Actually, pure OOS ranking is what is requested.
            # We just need to run on the Test segment and aggregate metrics.
            # The "Training" (Optimization) part is implicit in the "Selection" phase if we were optimizing params.
            # Since we generate random fixed strategies, we treat them as "candidates" and validate them on multiple OOS periods.

            test_df = df.iloc[train_end_idx:test_end_idx]

            if len(test_df) < 50: # Minimum bars
                continue

            res = engine_run_fn(test_df, strategy)
            metrics = res.get("metrics", {})

            results.append({
                "fold": i,
                "start": test_df.index[0],
                "end": test_df.index[-1],
                "metrics": metrics
            })

        return {
            "folds": results,
            "passed_folds": len([r for r in results if r["metrics"].get("sharpe", 0) > 0])
        }
