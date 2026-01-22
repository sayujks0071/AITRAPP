# Strategy Foundry
from typing import Any, Dict

import numpy as np
import pandas as pd

from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import calculate_metrics
from packages.strategy_foundry.backtest.sanity import check_sanity


class WalkForwardEvaluator:
    def __init__(self, engine: BacktestEngine):
        self.engine = engine

    def evaluate(self, df: pd.DataFrame, spec: Any, folds: int = 4) -> Dict[str, Any]:
        """
        Performs Walk Forward Evaluation.
        Returns aggregated OOS metrics.
        """
        if df.empty or len(df) < 500: # Min bars requirement
            return {}

        # Split indices
        n = len(df)
        fold_size = n // (folds + 1) # Simple equal split

        # We need at least 1 chunk for initial train (warmup) and 'folds' chunks for testing
        # Segments: [Train_Init] [Test_1] [Test_2] [Test_3] [Test_4]

        oos_metrics_list = []
        positive_folds = 0

        # We only care about OOS performance for ranking
        # We don't necessarily need to "Train" (optimize parameters) since we are generating random params.
        # We just need to "Validate" on OOS chunks.
        # But usually strategy is picked on IS and validated on OOS.
        # Here we are skipping optimization. We are just testing the candidate on multiple time periods.
        # So essentially k-fold cross validation or simply sliding window testing.

        # Let's treat each fold as an OOS period.
        # To avoid lookahead bias or regime bias, we test on multiple disjoint periods?
        # Or sequential?
        # Requirement: "Walk-forward OOS"

        # Implementation:
        # Iterate folds.
        # Test period i: start = i * fold_size, end = (i+1) * fold_size
        # We can just run the engine on the slice.
        # Important: Engine needs warmup data for indicators.
        # So pass [start - warmup : end] but only count trades in [start : end].

        warmup = 200

        full_trades = []

        for i in range(1, folds + 1):
            test_start_idx = i * fold_size
            test_end_idx = (i + 1) * fold_size if i < folds else n

            # Slice with warmup
            slice_start = max(0, test_start_idx - warmup)
            df_slice = df.iloc[slice_start:test_end_idx].copy()

            # Run Engine
            res = self.engine.run(df_slice, spec)

            # Filter trades that started inside the test window
            # Trade entry time >= df.index[test_start_idx]
            test_start_time = df.index[test_start_idx]

            slice_trades = [t for t in res["trades"] if t["entry_time"] >= test_start_time]

            if slice_trades:
                # Calculate metrics for this fold
                t_df = pd.DataFrame(slice_trades)

                # Equity curve for this slice (need to reconstruct)
                # Approximate daily returns from trades for Sharpe
                # It's hard to get exact daily returns without full equity curve.
                # Use engine's equity curve but sliced?
                eq_curve = res["equity_curve"]
                eq_curve = eq_curve[eq_curve.index >= test_start_time]

                d_eq = eq_curve.resample('D').last().dropna()
                d_ret = d_eq.pct_change().dropna()

                m = calculate_metrics(t_df, d_ret)
                oos_metrics_list.append(m)

                if m["pnl_net"] > 0 if "pnl_net" in m else m["profit_factor"] > 1.0:
                    positive_folds += 1

                full_trades.extend(slice_trades)
            else:
                # No trades in this fold
                pass

        # Aggregate OOS Metrics
        if not oos_metrics_list:
            return {}

        # Average Sharpe, CAGR, MaxDD
        avg_sharpe = np.mean([m["sharpe"] for m in oos_metrics_list])
        avg_calmar = np.mean([m["calmar"] for m in oos_metrics_list])
        avg_cagr = np.mean([m["cagr"] for m in oos_metrics_list])
        max_dd_worst = np.max([m["max_dd"] for m in oos_metrics_list])

        # Total Trades Sanity
        total_trades_df = pd.DataFrame(full_trades)
        sanity = check_sanity(total_trades_df, "mixed") # Timeframe str ambiguous here

        # Stability: standard deviation of Sharpe across folds
        sharpe_std = np.std([m["sharpe"] for m in oos_metrics_list])

        # Aggregate Return
        # Re-calculate aggregate metrics from full_trades list?
        # That's better for "Net Result".
        # But average of folds is better for "Robustness".

        return {
            "sharpe": avg_sharpe,
            "calmar": avg_calmar,
            "cagr": avg_cagr,
            "max_dd": max_dd_worst,
            "sharpe_std": sharpe_std,
            "positive_folds": positive_folds,
            "total_trades": len(full_trades),
            "profit_factor": np.mean([m["profit_factor"] for m in oos_metrics_list]),
            "avg_trade_pct": np.mean([m["avg_trade_pct"] for m in oos_metrics_list]),
            "sanity": sanity
        }
