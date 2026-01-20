"""Walk-forward analysis"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class WalkForward:
    def __init__(self, n_folds: int = 4, train_ratio: float = 0.7):
        self.n_folds = n_folds
        self.train_ratio = train_ratio

    def split_data(self, data: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Create expanding window splits or rolling?
        "Walk-forward OOS evaluation" usually implies rolling or expanding.
        Let's do simple chunks for robustness:
        Split total duration into N blocks.
        For each block, Train on (0..k), Test on (k+1)?
        Or Train/Test pairs.

        Let's do Time Series Split (Walk Forward):
        Total length L.
        Fold 1: Train [0 : L*0.4], Test [L*0.4 : L*0.55]
        Fold 2: Train [0 : L*0.55], Test [L*0.55 : L*0.7]
        ...
        Actually, simpler standard WF:
        Divide data into N+1 chunks.
        Fold i: Train on chunk i, Test on chunk i+1? No, that's not expanding.

        Let's use `sklearn.model_selection.TimeSeriesSplit` logic manually.
        """
        n = len(data)
        fold_size = n // (self.n_folds + 1)

        splits = []
        for i in range(1, self.n_folds + 1):
            train_end = i * fold_size
            test_end = (i + 1) * fold_size

            # Ensure train has enough data
            if train_end < 100: continue

            train_data = data.iloc[:train_end]
            test_data = data.iloc[train_end:test_end]

            splits.append((train_data, test_data))

        return splits

    def evaluate(self, candidate: StrategyCandidate, data: pd.DataFrame) -> Dict:
        """
        Run WF evaluation.
        """
        splits = self.split_data(data)
        oos_results = []

        fold_metrics = []

        for train_df, test_df in splits:
            # We only care about OOS performance for ranking
            # But we could check if Train was profitable? (Sanity)

            engine = BacktestEngine(test_df) # Test on OOS
            res = engine.run(candidate)
            metrics = calculate_metrics(res["equity"], res["trades"])

            oos_results.append(res)
            fold_metrics.append(metrics)

        # Aggregate OOS metrics
        # Combine all OOS trades to get aggregate stats?
        # Or average of metrics?

        # Concatenate all OOS equity curves to form a continuous OOS curve
        # Note: Capital resets each fold in loop above, need to stitch?
        # Simpler: just stitch trades.

        all_oos_trades = []
        for res in oos_results:
            all_oos_trades.append(res["trades"])

        if not all_oos_trades:
             return {"status": "failed", "reason": "no_data"}

        combined_trades = pd.concat(all_oos_trades) if all_oos_trades else pd.DataFrame()

        # We need a continuous equity curve for correct MaxDD calc over whole period
        # Re-construct equity from combined trades
        # Or just average the fold metrics?
        # Ranking criteria says: "Stability: fold-to-fold score variance"

        # Let's compute average Sharpe, and stability.
        sharpes = [m.get("sharpe", 0) for m in fold_metrics]
        calmars = [m.get("calmar", 0) for m in fold_metrics]

        avg_sharpe = np.mean(sharpes) if sharpes else -99
        avg_calmar = np.mean(calmars) if calmars else -99
        sharpe_stability = np.std(sharpes) if len(sharpes) > 1 else 0

        # Count positive folds
        positive_folds = sum(1 for m in fold_metrics if m.get("sharpe", -99) > 0)

        # Aggregate trades for total stats
        total_trades = sum(m.get("total_trades", 0) for m in fold_metrics)

        return {
            "avg_sharpe": avg_sharpe,
            "avg_calmar": avg_calmar,
            "sharpe_stability": sharpe_stability,
            "positive_folds": positive_folds,
            "total_trades": total_trades,
            "fold_metrics": fold_metrics,
            "n_folds": len(fold_metrics)
        }
