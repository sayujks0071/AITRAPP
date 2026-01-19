"""
Walk-forward analysis.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from packages.strategy_foundry.factory.grammar import Strategy
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class WalkForwardAnalyst:
    def __init__(self, folds: int = 3, train_ratio: float = 0.7):
        self.folds = folds
        self.train_ratio = train_ratio
        self.engine = BacktestEngine()

    def evaluate(self, strategy: Strategy, df: pd.DataFrame) -> Dict:
        """
        Run WFA.
        Splits data into K folds.
        For each fold: Train (IS) -> Test (OOS).
        Wait, WFA usually moves the window.
        Simple K-Fold or Expanding Window?
        "Walk-forward evaluation: 3–5 folds" implies expanding or rolling.
        Let's use Rolling Window or Anchored Walk Forward.

        Scheme:
        Divide data into Folds+1 segments.
        Fold 1: Train [0], Test [1]
        Fold 2: Train [0+1], Test [2]
        ...

        Or just simple time split?
        Common WFA:
        Total Data
        Split into N blocks.
        Step 1: Train on Block 1, Test on Block 2.
        Step 2: Train on Block 1+2, Test on Block 3.
        ...

        Since our strategies are NOT trainable (they are generated with fixed params),
        we effectively just VALIDATE on OOS.
        "Train" phase is just "See how it did", but we don't optimize params.
        So this is technically "Cross-Validation" of a fixed strategy, not "Walk-Forward Optimization".

        But the prompt says "Ranking uses OUT-OF-SAMPLE metrics only."
        So we just need to collect OOS performance.

        We will split the data into N chunks.
        We will ignore the first chunk (burn-in/IS proxy) and collect metrics on subsequent chunks?
        Or treat (Chunk 1 -> Test Chunk 2) as Fold 1.

        Actually, simpler:
        Just split data into K segments.
        We run the strategy on the whole history.
        Then we slice the Equity Curve / Trades into K segments.
        We report metrics for each OOS segment.
        Aggregate them.

        This is much faster than re-running.

        """
        # Run once on full data
        equity, trades = self.engine.run(strategy, df)

        if equity.empty:
            return {"valid": False, "reason": "No equity curve"}

        # Split into folds
        n = len(df)
        fold_size = n // (self.folds + 1) # +1 because first part is usually considered "In Sample" or just warmup

        oos_metrics = []

        for i in range(1, self.folds + 1):
            start_idx = i * fold_size
            end_idx = (i + 1) * fold_size if i < self.folds else n

            # Slice Equity
            # We need to re-normalize equity for the period to calculate period return
            sub_equity = equity.iloc[start_idx:end_idx]

            # Slice Trades
            # Trades in this range
            sub_trades = trades[
                (trades['entry_date'] >= equity.index[start_idx]) &
                (trades['entry_date'] <= equity.index[end_idx-1])
            ] if not trades.empty else pd.DataFrame()

            metrics = calculate_metrics(sub_equity, sub_trades)
            oos_metrics.append(metrics)

        # Aggregate OOS metrics
        # Average Sharpe, Total Return, etc.

        avg_sharpe = np.mean([m['sharpe'] for m in oos_metrics])
        avg_cagr = np.mean([m['cagr'] for m in oos_metrics])
        avg_calmar = np.mean([m['calmar'] for m in oos_metrics])

        # Stability of Sharpe
        sharpes = [m['sharpe'] for m in oos_metrics]
        stability = 1.0 / (np.std(sharpes) + 0.01)

        return {
            "valid": True,
            "folds": oos_metrics,
            "avg_oos_sharpe": avg_sharpe,
            "avg_oos_cagr": avg_cagr,
            "avg_oos_calmar": avg_calmar,
            "stability": stability,
            "full_equity": equity,
            "full_trades": trades,
            "full_metrics": calculate_metrics(equity, trades)
        }
