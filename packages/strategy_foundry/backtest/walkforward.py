import pandas as pd
import numpy as np
from typing import List, Dict, Any
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import Strategy
import structlog

logger = structlog.get_logger(__name__)

class WalkForwardEvaluator:
    def __init__(self, n_folds: int = 3):
        self.n_folds = n_folds
        self.engine = BacktestEngine()

    def evaluate(self, strategy: Strategy, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform walk-forward evaluation.
        Splits data into N folds.
        For simplicity in this MVP:
        - We just split data into N equal chunks.
        - We treat each chunk as OOS (Out of Sample) for evaluation purposes
          (since we are not optimizing params on IS, we are generating random ones).
        - So effectively, the entire history is OOS for random search.

        However, to simulate stability, we check consistency across folds.
        """
        if len(df) < 252:
            return {"valid": False, "reason": "Insufficient data"}

        fold_size = len(df) // self.n_folds

        fold_metrics = []
        equity_curves = []

        for i in range(self.n_folds):
            start = i * fold_size
            end = (i + 1) * fold_size if i < self.n_folds - 1 else len(df)

            fold_df = df.iloc[start:end]
            metrics = self.engine.run(strategy, fold_df)

            fold_metrics.append(metrics)
            if "equity_curve" in metrics:
                equity_curves.extend(metrics["equity_curve"].values()) # Just accumulating values for now

        # Aggregate Metrics (OOS average)
        avg_sharpe = np.mean([m["sharpe"] for m in fold_metrics])
        avg_cagr = np.mean([m["cagr"] for m in fold_metrics])
        worst_dd = np.min([m["max_drawdown"] for m in fold_metrics])
        total_trades = sum([m["trades"] for m in fold_metrics])

        positive_folds = sum([1 for m in fold_metrics if m["total_return"] > 0])

        # Check stability (std dev of sharpe)
        sharpe_dispersion = np.std([m["sharpe"] for m in fold_metrics])

        # Full run for final equity curve
        full_metrics = self.engine.run(strategy, df)

        return {
            "valid": True,
            "avg_sharpe": avg_sharpe,
            "avg_cagr": avg_cagr,
            "worst_drawdown": worst_dd,
            "total_trades": total_trades,
            "positive_folds": positive_folds,
            "sharpe_dispersion": sharpe_dispersion,
            "full_metrics": full_metrics,
            "fold_metrics": fold_metrics
        }
