import pandas as pd
from typing import List, Dict, Any, Tuple
from .engine import run_backtest
from .metrics import calculate_metrics

class WalkForwardEvaluator:
    def __init__(self, folds: int = 4, train_ratio: float = 0.7):
        self.folds = folds
        self.train_ratio = train_ratio

    def split_data(self, df: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Expanding Window Walk-Forward.
        """
        n = len(df)
        fold_size = n // (self.folds + 1)
        splits = []

        # Start with 2 chunks for training
        train_end = fold_size * 2

        for i in range(self.folds):
            test_end = train_end + fold_size
            if test_end > n: break

            train_df = df.iloc[:train_end]
            test_df = df.iloc[train_end:test_end]

            splits.append((train_df, test_df))

            # Expand training window
            train_end += fold_size

        return splits

    def evaluate(self, candidate, df: pd.DataFrame, costs: Dict[str, float]) -> Dict[str, Any]:
        splits = self.split_data(df)
        fold_results = []

        oos_returns = []
        oos_trades = []

        for train_df, test_df in splits:
            # We don't optimize parameters here (that would be true Walk-Forward Optimization).
            # We are doing Walk-Forward *Validation* of a fixed strategy.
            # So we just run the strategy on the Test fold.

            # Note: To correctly simulate "run on test", we need context from train (like lookback).
            # The backtest engine handles independent chunks roughly, but indicators need warm-up.
            # Ideally we compute indicators on full DF, then slice.
            # Our Candidate.generate_positions takes a DF.
            # If we pass sliced DF, indicators at start are NaN.
            # Better: Pass full DF and a mask/slice range.
            # But generate_positions returns Series for passed DF.

            # Hack: Pass `test_df` but with some warm-up rows from `train_df`.
            warmup = 200
            if len(train_df) > warmup:
                test_with_warmup = pd.concat([train_df.iloc[-warmup:], test_df])
                warmup_len = warmup
            else:
                test_with_warmup = pd.concat([train_df, test_df])
                warmup_len = len(train_df)

            positions = candidate.generate_positions(test_with_warmup)

            # Slice back to test period
            positions_test = positions.iloc[warmup_len:]
            df_test = test_with_warmup.iloc[warmup_len:]

            res = run_backtest(df_test, positions_test, costs)

            metrics = calculate_metrics(res['returns'], res['trades'])
            fold_results.append(metrics)

            oos_returns.append(res['returns'])
            oos_trades.append(res['trades'])

        # Aggregate OOS results
        if not oos_returns:
            return {}

        full_oos_returns = pd.concat(oos_returns)
        full_oos_trades = pd.concat(oos_trades) if any(not t.empty for t in oos_trades) else pd.DataFrame()

        overall_metrics = calculate_metrics(full_oos_returns, full_oos_trades)

        # Stability check: number of positive folds
        positive_folds = sum(1 for f in fold_results if f.get('cagr', 0) > 0)

        return {
            "metrics": overall_metrics,
            "fold_results": fold_results,
            "positive_folds": positive_folds,
            "n_folds": len(fold_results)
        }
