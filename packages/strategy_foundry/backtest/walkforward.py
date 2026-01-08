"""
Walk-Forward Analysis (WFA) implementation.
"""
import pandas as pd
import numpy as np
import structlog
from typing import List, Dict, Any
from packages.strategy_foundry.factory.grammar import StrategyConfig
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.selection.ranker import Ranker

logger = structlog.get_logger(__name__)

class WalkForwardValidator:
    def __init__(self, engine: BacktestEngine, ranker: Ranker, folds: int = 4, is_fast_mode: bool = False):
        self.engine = engine
        self.ranker = ranker
        self.folds = 2 if is_fast_mode else folds

    def validate(self, strategy: StrategyConfig, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform Walk-Forward Validation.

        Splits data into N folds.
        For each fold:
          - Train on expanding window (or rolling)
          - Test on next segment

        Returns aggregated OOS metrics.
        """
        if len(data) < 500: # Minimum data requirement
            return {"valid": False, "reason": "Insufficient Data"}

        # Define split points
        # Simple approach: Split data into Folds+1 segments.
        # Train on [0..i], Test on [i+1]

        segment_size = len(data) // (self.folds + 1)

        oos_trades = []
        fold_metrics = []

        # We start testing from the 2nd segment
        for i in range(1, self.folds + 1):
            train_end = i * segment_size
            test_start = train_end
            test_end = (i + 1) * segment_size if i < self.folds else len(data)

            # Train Data (Expanding Window)
            # train_data = data.iloc[:train_end]
            # Actually, for WFA we usually optimize on Train.
            # But here we are validating a fixed strategy generated randomly.
            # So we just run it on Test and collect metrics.
            # We check if it performs consistently.
            # "Train results may be logged but not used for score" -> User requirement.

            test_data = data.iloc[test_start:test_end]

            # Run Backtest on OOS Fold
            res = self.engine.run(strategy, test_data)

            # If we need to "optimize", we would do it here on train_data.
            # But since we are doing random generation, the "Training" is essentially
            # the generation phase (which selected this candidate).
            # Wait, usually generation happens on a specific dataset.
            # The user says: "Generate N candidates... Backtest + walk-forward".
            # The candidate is generated with random params.
            # We should probably treat the entire WFA as the evaluation of the candidate.

            fold_trades = res["trades"]
            oos_trades.extend(fold_trades)

            metrics = self.ranker.calculate_metrics(fold_trades)
            fold_metrics.append(metrics)

        # Aggregate OOS Metrics
        total_oos_metrics = self.ranker.calculate_metrics(oos_trades)

        # Stability: Variance of Sharpe across folds
        sharpes = [m["sharpe"] for m in fold_metrics]
        stability = 1.0 - np.std(sharpes) if len(sharpes) > 1 else 0.5

        # Check positive folds
        positive_folds = sum(1 for m in fold_metrics if m["pnl_positive"])

        total_oos_metrics["stability"] = stability
        total_oos_metrics["positive_folds"] = positive_folds
        total_oos_metrics["total_folds"] = self.folds

        return {
            "valid": True,
            "metrics": total_oos_metrics,
            "fold_metrics": fold_metrics
        }

