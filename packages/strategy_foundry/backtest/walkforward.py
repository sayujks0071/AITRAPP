"""
Strategy Foundry - Walk Forward Analysis.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import compute_metrics
import structlog

logger = structlog.get_logger(__name__)

class WalkForwardAnalyst:
    def __init__(self, data: pd.DataFrame, n_folds: int = 4):
        self.data = data
        self.n_folds = n_folds

    def run(self, strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run Walk-Forward Analysis.
        Splits data into N folds.
        For each fold:
          - (Optional) Optimize on In-Sample (IS) -> We skip opt for now as we generate random fixed params.
          - Evaluate on Out-Of-Sample (OOS)

        Since we are selecting from random candidates, we treat the 'Training' phase
        as just verification that it worked in the past, but the Score comes from OOS.

        Actually, pure WF usually implies re-optimization.
        Here we have fixed strategies (candidates).
        So we are essentially Cross-Validating them or testing robustness over time.

        We will split time into N blocks.
        OOS Performance is the concatenation of the test folds?
        Or just average metrics across folds?

        Let's do Expanding Window WF.
        Train:Start..T, Test: T..T+k

        Since params are fixed (no optimization step inside the fold),
        this effectively measures stability of the fixed parameters over time.
        """

        # Split data
        n = len(self.data)
        if n < 500: # Need enough data
            return {"valid": False, "reason": "Insufficient data"}

        fold_size = n // (self.n_folds + 1)

        oos_trades = []
        oos_equity = [] # Hard to stitch equity exactly without bias, but let's try.

        fold_metrics = []

        engine = BacktestEngine(self.data)

        # We simulate "Production" usage:
        # At time T, we pick this strategy. Does it work in T+1?

        for i in range(1, self.n_folds + 1):
            train_end = i * fold_size
            test_end = (i + 1) * fold_size if i < self.n_folds else n

            # test_data = self.data.iloc[train_end:test_end]
            # We need to run engine on full data but slice results to handle lookback correctly?
            # Or run engine on slice? Engine needs warmup.
            # Best: Run engine on slice with some warmup from train.

            warmup = 100
            start_idx = max(0, train_end - warmup)

            chunk_data = self.data.iloc[start_idx:test_end].copy()

            chunk_engine = BacktestEngine(chunk_data)
            res = chunk_engine.run(strategy_config)

            # Extract OOS portion
            # The result indices are dates.
            # We want trades that exited in OOS period (train_end date to test_end date)

            split_date = self.data.index[train_end]

            chunk_trades = res["trades"]
            if not chunk_trades.empty:
                # Filter trades that exited after split_date
                oos_tr = chunk_trades[chunk_trades["exit_date"] > split_date]
                oos_trades.append(oos_tr)

            # Compute metrics for this fold
            # Need equity curve slice
            eq = res["equity_curve"]
            oos_eq = eq[eq.index > split_date]

            if not oos_eq.empty:
                m = compute_metrics(oos_eq, oos_tr if not chunk_trades.empty else pd.DataFrame())
                fold_metrics.append(m)

        # Aggregate OOS results
        if not oos_trades:
            return {"valid": False, "reason": "No OOS trades"}

        all_oos_trades = pd.concat(oos_trades)

        if all_oos_trades.empty:
             return {"valid": False, "reason": "No OOS trades in combined"}

        # Stitch equity curve approx (cumulative return)
        # Or just re-run on full dataset and call it "Full Backtest"
        # but pure OOS metrics are better derived from the folds.

        # Let's compute aggregate metrics from all OOS trades
        # Reconstructing a synthetic equity curve from trades
        # Assuming fixed capital per trade or compounding?
        # Let's simple sum returns for metric proxy or use average fold metrics.

        avg_sharpe = np.mean([m.get("sharpe", 0) for m in fold_metrics])
        avg_cagr = np.mean([m.get("cagr", 0) for m in fold_metrics])

        # Full OOS Trade Analysis
        # We can treat the sequence of OOS trades as one track record
        all_oos_trades.sort_values("entry_date", inplace=True)

        return {
            "valid": True,
            "metrics": {
                "sharpe": avg_sharpe,
                "cagr": avg_cagr,
                "folds": fold_metrics,
                "total_trades": len(all_oos_trades)
            },
            "trades": all_oos_trades
        }
