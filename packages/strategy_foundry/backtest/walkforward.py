import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Any
from packages.strategy_foundry.factory.grammar import Strategy
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class WalkForwardEvaluator:
    def __init__(self, engine: BacktestEngine, n_folds: int = 3):
        self.engine = engine
        self.n_folds = n_folds

    def evaluate(self, strategy: Strategy, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform Walk-Forward Analysis.
        Splits data into K folds.
        For simplicity in this MVP, we do K-Fold Cross Validation or Expanding Window?
        User asked for "Walk-forward evaluation... 3-5 folds".
        Standard WF: Train on [0..T], Test on [T..T+k].
        Since we are *generating* strategies (not optimizing params per se),
        we treat the "generation" phase as Training on the WHOLE past?
        No, that causes overfitting.

        The 'Generator' creates random strategies. We need to validate them.
        We should evaluate on Out-Of-Sample data.

        Approach:
        Split data into chunks.
        For each chunk i (Test), we could have trained on 0..i-1.
        But since strategies are fixed (randomly generated parameters),
        we just run the fixed strategy on the Test Fold and aggregate results.

        Wait, if we don't optimize params, Walk-Forward is just "Backtest on whole history partitioned".
        The value comes if we select the best strategy based on Train folds and verify on Test folds.

        But here we are just filtering candidates.
        So we just run backtest on the whole period, but calculate metrics on the "Out Of Sample" segments?
        Or maybe the requirement implies:
        Train (Optimize) -> Test.
        But we skip Optimization (Grid Search).

        So, we will just run the strategy on the ENTIRE dataset,
        but compute stability metrics across folds.

        Actually, let's treat the *most recent* fold as OOS for "Live Selection"?
        Or just split into N folds and report metrics for each, plus aggregate.

        Let's do this:
        Divide DF into N equal time chunks.
        Run backtest on each chunk.
        Collect metrics for each chunk.

        Return:
        - Aggregate Metrics (Whole period)
        - Fold Metrics
        - Stability Score (Variance of Sharpe across folds)
        """
        n = len(df)
        fold_size = n // self.n_folds

        fold_metrics = []

        all_res = self.engine.run(strategy, df)
        trades_all = all_res.get("trades", pd.DataFrame())

        if trades_all.empty:
            return {"valid": False, "reason": "No trades"}

        # Calculate metrics per fold based on time
        start_time = df.index[0]
        end_time = df.index[-1]
        total_duration = end_time - start_time
        fold_duration = total_duration / self.n_folds

        for i in range(self.n_folds):
            f_start = start_time + (fold_duration * i)
            f_end = start_time + (fold_duration * (i+1))

            # Filter trades in this window
            # Note: A trade might straddle folds. We use exit_time.
            mask = (trades_all["exit_time"] >= f_start) & (trades_all["exit_time"] < f_end)
            f_trades = trades_all[mask]

            m = calculate_metrics(f_trades)
            m["fold"] = i
            fold_metrics.append(m)

        # Aggregate (OOS) - effectively whole period is OOS if we didn't train on it.
        # Since strategies are random, the whole history is OOS.
        agg_metrics = calculate_metrics(trades_all)

        # Calculate Stability
        sharpes = [m["sharpe"] for m in fold_metrics]
        stability = 1.0 / (np.std(sharpes) + 0.1) # Inverse variance proxy

        # Check Sanity
        # - trades < 30 (FAST_MODE: 10) -> handled by caller or here
        # - MaxDD > 35%

        return {
            "valid": True,
            "metrics": agg_metrics,
            "fold_metrics": fold_metrics,
            "stability": stability,
            "trades": trades_all
        }
