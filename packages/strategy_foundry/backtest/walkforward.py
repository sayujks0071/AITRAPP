import pandas as pd
import numpy as np

class WalkForwardEvaluator:
    def __init__(self, engine):
        self.engine = engine

    def evaluate(self, df: pd.DataFrame, spec: dict, folds: int = 4, train_ratio: float = 0.7) -> dict:
        """
        Walk-forward evaluation.
        Splits data into K folds.
        Train on fold i, Test on fold i (OOS).
        Actually WFE usually: Train on [0..i], Test on [i+1].
        Or Rolling Window: Train [i-W..i], Test [i..i+S].

        We will use Anchored Walk Forward for simplicity and robustness:
        Fold 1: Train 0-50%, Test 50-60%
        Fold 2: Train 0-60%, Test 60-70%
        ...
        """
        n = len(df)
        if n < 500: # Min data requirement
             return {}

        # Split data into folds
        # e.g. 4 folds over the last 40% of data?
        # Let's say we reserve first 50% for initial training.
        # Remaining 50% divided into 'folds' chunks.

        oos_start_idx = int(n * (1 - 1/(folds+1))) # Just a heuristic?
        # Better:
        # Total OOS period = 40% of data.
        # Split that 40% into `folds` segments.

        oos_ratio = 0.4
        oos_total_len = int(n * oos_ratio)
        fold_len = oos_total_len // folds
        start_oos = n - oos_total_len

        fold_metrics = []
        aggregate_equity = []

        for i in range(folds):
            train_end = start_oos + (i * fold_len)
            test_end = train_end + fold_len

            # Train (In-Sample) - Optional: Optimize here?
            # The prompt says "Walk-forward evaluation... Ranking uses OUT-OF-SAMPLE metrics only."
            # It implies we just *test* the candidate on OOS.
            # The candidate (spec) is already generated (fixed params).
            # So we don't need to re-optimize params on Train. We just need to validate performance on OOS.
            # So we can simply run the strategy on the OOS segment.
            # Wait, usually WFE implies optimization.
            # But here we are generating random candidates.
            # So the "Training" is implicit in the generation/selection?
            # Or does "Generate N candidates" mean we generated them with random params, and we just want to see if they hold up?
            # Yes, "Ranking uses OUT-OF-SAMPLE metrics".
            # So we strictly care about OOS performance.
            # We can run the strategy on the full OOS period?
            # Or do we want to simulate the experience of "We picked this strategy at time T, how did it do T+1?"

            # If we just test on one OOS block, it's simple Hold-Out.
            # WFE implies multiple steps.
            # Let's run on each OOS fold and aggregate.

            test_df = df.iloc[train_end:test_end]
            res = self.engine.run(test_df, spec)
            m = res["metrics"]
            m["fold"] = i + 1
            fold_metrics.append(m)

        # Aggregate OOS metrics
        # We can average them or re-calculate from concatenated trades
        # Re-calc is better.

        # But we don't have concatenated trades easily unless we store them.
        # Let's just average Sharpe, etc. or count success.

        avg_sharpe = np.mean([m.get("sharpe", 0) for m in fold_metrics])
        positive_folds = sum(1 for m in fold_metrics if m.get("total_return", 0) > 0)

        # Also run on FULL OOS to get total stats?
        full_oos_df = df.iloc[start_oos:]
        oos_res = self.engine.run(full_oos_df, spec)
        oos_metrics = oos_res["metrics"]

        oos_metrics["avg_fold_sharpe"] = avg_sharpe
        oos_metrics["positive_folds"] = positive_folds

        return oos_metrics
