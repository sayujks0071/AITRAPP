import pandas as pd
from typing import List, Tuple, Dict
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class WalkForward:
    def __init__(self, data: pd.DataFrame, engine: BacktestEngine, folds: int = 4):
        self.data = data
        self.engine = engine
        self.folds = folds

    def run(self, candidate: StrategyCandidate) -> Dict:
        """
        Run walk-forward analysis.
        Splits data into K folds.
        Train on [0..i], Test on [i+1].
        Actually, standard Walk Forward is Expanding or Rolling.
        "Train on past, test on next".

        We will use simple K-Fold time-series split:
        Split data into K+1 segments.
        Fold 1: Train Seg 0, Test Seg 1
        Fold 2: Train Seg 0+1, Test Seg 2 (Expanding window)

        Returns aggregated OOS metrics.
        """
        n = len(self.data)
        if n < 500: # Not enough data
            return {"status": "skipped", "reason": "insufficient_data"}

        segment_size = n // (self.folds + 1)

        fold_results = []
        all_oos_trades = []

        for i in range(self.folds):
            # Train: 0 to (i+1)*segment_size
            # Test: (i+1)*segment_size to (i+2)*segment_size
            train_end = (i + 1) * segment_size
            test_end = (i + 2) * segment_size
            if i == self.folds - 1:
                test_end = n # Catch remainder

            train_data = self.data.iloc[:train_end]
            test_data = self.data.iloc[train_end:test_end]

            # We don't "train" parameters here (parameters are fixed in candidate).
            # We just EVALUATE on OOS.
            # If we were optimizing, we would optimize on train.
            # Here we are validating if the *randomly generated* strategy holds up.
            # So we just run on Test data.
            # But we might want to check Train to see if it was profitable there?
            # The prompt says "Generate ... Backtest ... Rank with anti-overfit".
            # "Use walk-forward OOS evaluation".

            # Since params are fixed, "Walk Forward" here effectively means
            # "Performance Consistency Check across time blocks".

            # Run on Test
            # Need to warm up indicators?
            # Pass a bit of train data for warmup?
            warmup = 100
            if len(test_data) < warmup: continue

            # Slice with warmup
            test_slice_start = train_end - warmup
            if test_slice_start < 0: test_slice_start = 0

            # Create a view for the engine that includes warmup
            # But we only count trades starting after train_end
            combined_view = self.data.iloc[test_slice_start:test_end]

            # Temporary engine with slice
            # We assume engine is stateless except for config
            slice_engine = BacktestEngine(combined_view, self.engine.costs)

            trades = slice_engine.run(candidate)

            # Filter trades that started in the test period
            if not trades.empty:
                cutoff = self.data.index[train_end]
                oos_trades = trades[trades["entry_time"] >= cutoff]

                metrics = calculate_metrics(oos_trades)
                fold_results.append(metrics)
                all_oos_trades.append(oos_trades)
            else:
                fold_results.append(calculate_metrics(pd.DataFrame()))

        # Aggregate OOS
        if all_oos_trades:
            merged_trades = pd.concat(all_oos_trades)
            total_metrics = calculate_metrics(merged_trades)
        else:
            total_metrics = calculate_metrics(pd.DataFrame())

        return {
            "status": "ok",
            "folds": fold_results,
            "aggregate": total_metrics
        }
