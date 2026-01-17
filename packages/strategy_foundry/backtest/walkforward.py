import pandas as pd
import numpy as np
import structlog
from typing import List, Dict, Any
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyCandidate

logger = structlog.get_logger(__name__)

class WalkForwardEvaluator:
    """
    Implements Walk-Forward Validation.
    """
    def __init__(self, n_folds: int = 4, train_ratio: float = 0.7):
        self.n_folds = n_folds
        self.train_ratio = train_ratio

    def evaluate(self, candidate: StrategyCandidate, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Run walk-forward evaluation.

        Splits data into K folds (rolling or expanding).
        For robustness, we use rolling window validation:
        [Train 1][Test 1]
                 [Train 2][Test 2]
                          ...

        Returns aggregated OOS metrics.
        """
        n = len(data)
        if n < 100: # minimal bars check
             return {"sharpe": 0, "status": "insufficient_data"}

        # Simple rolling folds
        fold_size = n // (self.n_folds + 1)
        # We need at least one training block + n_folds testing blocks?
        # Or just split total data into (k+1) chunks?

        # Let's do:
        # Fold size = total / (folds + 1)
        # Train = 2 chunks, Test = 1 chunk
        # Rolling forward

        chunk_size = int(n / (self.n_folds + 1))

        oos_trades = []
        fold_scores = []

        for i in range(self.n_folds):
            start_idx = i * chunk_size
            train_end_idx = start_idx + (chunk_size * 2) # Use 2 chunks for training
            test_end_idx = train_end_idx + chunk_size

            if test_end_idx > n:
                break

            train_data = data.iloc[start_idx:train_end_idx]
            test_data = data.iloc[train_end_idx:test_end_idx]

            # Run on TEST data (strictly OOS)
            # Note: In true WF, we might optimize params on Train, then run on Test.
            # Here, the candidate already has params fixed (generated).
            # So we are just validating STABILITY of these params across time.

            engine = BacktestEngine(test_data)
            res = engine.run(candidate)

            trades = res.get("trades", pd.DataFrame())
            metrics = res.get("metrics", {})

            if not trades.empty:
                oos_trades.append(trades)
                fold_scores.append(metrics.get("sharpe", 0))
            else:
                fold_scores.append(0)

        # Aggregate OOS trades
        if oos_trades:
            all_oos_trades = pd.concat(oos_trades)
            # Re-calculate metrics on consolidated OOS trades
            # This gives the "Walk Forward Equity Curve" stats
            from packages.strategy_foundry.backtest.metrics import calculate_metrics
            agg_metrics = calculate_metrics(all_oos_trades)

            # Add stability metrics
            agg_metrics["fold_sharpe_std"] = np.std(fold_scores)
            agg_metrics["positive_folds"] = sum(1 for s in fold_scores if s > 0)

            return agg_metrics
        else:
            return {"sharpe": 0, "status": "no_trades"}
