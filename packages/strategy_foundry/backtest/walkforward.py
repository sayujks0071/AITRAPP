"""
Walk-Forward Analysis.
Implements the evaluation logic.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import calculate_metrics
from packages.strategy_foundry.factory.grammar import StrategyCandidate
import structlog

logger = structlog.get_logger(__name__)

class WalkForward:
    def __init__(self, folds: int = 4):
        self.folds = folds
        self.engine = BacktestEngine()

    def evaluate(self, df: pd.DataFrame, candidate: StrategyCandidate) -> Dict[str, Any]:
        """
        Run Walk-Forward Analysis.
        Splits data into K folds (expanding window or rolling?).
        Requirement: "expanding window for training and a rolling window for testing" (from memory)
        or just standard WF.

        Let's use simple TimeSeriesSplit logic.
        """
        n = len(df)
        if n < 500: # Need enough data
            return {"valid": False, "reason": "Insufficient data"}

        fold_size = n // (self.folds + 1)

        oos_metrics = []
        equity_curves = []
        trades_list = []

        # We only care about OOS performance for ranking.
        # But we simulate the strategy on OOS data.
        # Since the strategy candidates are static (grammar generated parameters are fixed),
        # "Training" here effectively means "Validation" if we were optimizing parameters.
        # But here we are just validating if the *fixed parameters* work across time.
        # So we can just backtest the whole period and split the results,
        # OR run backtest on chunks.
        # Running on chunks is safer to ensure no lookahead leakage across folds (though engine prevents it).
        # Actually, running once on full data and slicing the equity curve is faster and equivalent
        # for static parameters.

        full_result = self.engine.run(df, candidate)
        full_curve = full_result["equity_curve"]
        full_trades = full_result["trades"]

        if full_curve.empty:
            return {"valid": False, "reason": "No trades"}

        # Split into folds for stability analysis
        # We treat the whole history as "Out of Sample" test of the random candidate?
        # No, usually WF implies optimizing on Train, testing on Test.
        # Since we generated random parameters, the entire history is effectively OOS
        # (assuming we haven't seen this data during generation).
        # However, to measure *stability*, we split into periods.

        # Let's divide the full curve into N segments and compute metrics for each.
        segment_len = len(full_curve) // self.folds

        fold_results = []
        positive_folds = 0

        for i in range(self.folds):
            start = i * segment_len
            end = (i + 1) * segment_len if i < self.folds - 1 else len(full_curve)

            segment_curve = full_curve.iloc[start:end]
            if segment_curve.empty:
                continue

            # Filter trades in this period
            t_start = segment_curve.index[0]
            t_end = segment_curve.index[-1]
            if not full_trades.empty:
                segment_trades = full_trades[(full_trades["exit_date"] >= t_start) & (full_trades["exit_date"] <= t_end)]
            else:
                segment_trades = pd.DataFrame()

            # Rebase curve to 1.0 or start val for calc
            # Metrics func handles it
            m = calculate_metrics(segment_curve["equity"], segment_trades)
            fold_results.append(m)

            if m.get("sharpe", 0) > 0:
                positive_folds += 1

        # Aggregate Metrics (Average of folds? Or Global?)
        # Global metrics are best for overall performance.
        global_metrics = calculate_metrics(full_curve["equity"], full_trades)

        # Stability: Std Dev of Fold Sharpes
        sharpes = [m.get("sharpe", 0) for m in fold_results]
        stability = 1.0 / (np.std(sharpes) + 0.1) # Higher is better

        return {
            "valid": True,
            "metrics": global_metrics,
            "folds": fold_results,
            "positive_folds": positive_folds,
            "stability_score": stability,
            "equity_curve": full_curve,
            "trades": full_trades
        }
