import pandas as pd
import numpy as np
from typing import Dict, Any, List
import logging
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import calculate_metrics
from packages.strategy_foundry.backtest.costs import CostModel
from packages.strategy_foundry.factory.grammar import StrategyConfig
import yaml
import os

logger = logging.getLogger(__name__)

# Load config for defaults
def load_config():
    path = "packages/strategy_foundry/configs/foundry.yaml"
    if os.path.exists(path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    return {}

class WalkForwardEvaluator:
    def __init__(self, df: pd.DataFrame, folds: int = 4):
        self.df = df
        self.folds = folds

        conf = load_config().get('execution', {})
        self.cost_model = CostModel(
            slippage_bps_per_side=conf.get('slippage_bps_per_side', 5.0),
            brokerage_per_order=conf.get('brokerage_per_order', 20.0),
            spread_guard_bps=conf.get('spread_guard_bps', 2.0),
            tax_bps=conf.get('tax_bps', 3.0)
        )
        self.engine = BacktestEngine(self.cost_model)

    def evaluate(self, candidate: StrategyConfig) -> Dict[str, Any]:
        """
        Performs Walk-Forward Analysis.
        Splits data into K folds.
        For each fold: Train (skipped here as strategy is fixed) -> Test (OOS).
        We only care about OOS performance for validation.
        The prompt implies: "OOS evaluation for ranking".
        """
        if self.df is None or self.df.empty:
            return {}

        n = len(self.df)
        fold_size = n // self.folds

        oos_metrics_list = []
        all_trades = []

        for k in range(self.folds):
            # OOS window: segment k
            start_idx = k * fold_size
            end_idx = (k + 1) * fold_size if k < self.folds - 1 else n

            # Ensure we have enough data (lookback needed)
            # We need to slice with buffer for indicators?
            # Ideally passing the whole DF and start/end indices to engine is better,
            # but current engine takes DF.
            # We slice with buffer of ~200 bars.
            buffer = 200
            slice_start = max(0, start_idx - buffer)

            # Slice DF
            df_slice = self.df.iloc[slice_start:end_idx].copy()

            # Run Backtest
            trades = self.engine.run(df_slice, candidate)

            # Filter trades that started inside the actual OOS window
            # Trade entry_idx is relative to df_slice.
            # Actual index = entry_idx + slice_start
            if not trades.empty:
                trades['global_entry_idx'] = trades['entry_idx'] + slice_start
                # Filter: global_entry_idx >= start_idx
                trades = trades[trades['global_entry_idx'] >= start_idx]

                # Append to all trades
                all_trades.append(trades)

                # Calculate Fold Metrics
                m = calculate_metrics(trades)
                oos_metrics_list.append(m)
            else:
                 oos_metrics_list.append(calculate_metrics(pd.DataFrame()))

        # Aggregate Metrics (Average of OOS folds? or concatenated?)
        # "Stability: rolling Sharpe dispersion"
        # We calculate metrics on concatenated trades for overall score,
        # and use fold metrics for stability.

        if all_trades:
            total_trades_df = pd.concat(all_trades, ignore_index=True)
            overall_metrics = calculate_metrics(total_trades_df)
        else:
            total_trades_df = pd.DataFrame()
            overall_metrics = calculate_metrics(pd.DataFrame())

        # Stability Stats
        sharpes = [m['sharpe'] for m in oos_metrics_list]
        sharpe_std = np.std(sharpes) if len(sharpes) > 0 else 0.0

        positive_folds = sum(1 for m in oos_metrics_list if m['net_return'] > 0)

        # Intraday Sanity: "Late Day Dependence"
        # Check if > 50% profit comes from last 30 mins trades?
        # Check trades exit time?
        # We have 'exit_idx'.
        # This requires access to time. global_entry_idx allows mapping back.

        return {
            "overall": overall_metrics,
            "folds": oos_metrics_list,
            "stability": {
                "sharpe_std": sharpe_std,
                "positive_folds": positive_folds
            },
            "total_trades_count": len(total_trades_df)
        }
