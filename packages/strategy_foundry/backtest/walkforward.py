"""
Walk-forward analysis logic.
"""
import pandas as pd
import structlog
from typing import List, Dict, Any, Tuple
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import calculate_metrics
from packages.strategy_foundry.factory.grammar import StrategySpec

logger = structlog.get_logger(__name__)

class WalkForwardAnalyst:
    def __init__(self, data: pd.DataFrame, n_folds: int = 4):
        self.data = data
        self.n_folds = n_folds

    def run(self, strategy: StrategySpec) -> Dict[str, Any]:
        """
        Run walk-forward analysis.
        Splits data into K folds (Expanding Window or Rolling).

        Since we have limited intraday data (e.g. 60 days), 4 folds means ~15 days each.
        We use expanding window training?
        Or just OOS testing?

        Standard WF:
        Train 1 -> Test 1
        Train 1+Test 1 -> Test 2
        ...

        Given the limited data and "Aggressive" nature, maybe we treat chunks as OOS?
        Or simply split into 4 equal chunks and run backtest on each to check consistency?
        The prompt says: "Walk-forward OOS evaluation... Require OOS evaluation for ranking".

        Let's implement equal splits.
        Fold 1: Days 0-25%
        Fold 2: Days 25-50%
        ...

        We run the strategy on each fold independently.
        Ideally we "optimize" on train and test on OOS.
        But here we generated a STATIC strategy candidate.
        So we just validate its performance across different time periods (OOS validation).

        This effectively tests "robustness over time".
        """
        if self.data.empty:
            return {}

        # Split data by time
        total_rows = len(self.data)
        fold_size = total_rows // self.n_folds

        folds_metrics = []
        equity_curves = []
        all_trades = []

        consistency_score = 0

        for i in range(self.n_folds):
            start_idx = i * fold_size
            end_idx = (i + 1) * fold_size if i < self.n_folds - 1 else total_rows

            fold_data = self.data.iloc[start_idx:end_idx].copy()

            engine = BacktestEngine(fold_data)
            results = engine.run(strategy)

            metrics = calculate_metrics(results["trades"], results["equity_curve"])
            folds_metrics.append(metrics)

            # Consistency check (profit factor > 1)
            if metrics["profit_factor"] > 1.05 and metrics["trades"] > 5:
                consistency_score += 1

            equity_curves.append(results["equity_curve"])
            all_trades.append(results["trades"])

        # Aggregate metrics (OOS weighted?)
        # Just average them or sum them?
        # A concatenated backtest is better for overall stats.

        combined_trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
        combined_equity = pd.concat(equity_curves) # Index might overlap if not careful, but here we sliced linearly

        overall_metrics = calculate_metrics(combined_trades, combined_equity)

        return {
            "overall": overall_metrics,
            "folds": folds_metrics,
            "consistency": consistency_score, # e.g., 3/4
            "n_folds": self.n_folds
        }
