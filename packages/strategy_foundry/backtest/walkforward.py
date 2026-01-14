import pandas as pd
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import MetricsCalculator
from packages.strategy_foundry.factory.grammar import StrategyConfig

class WalkForwardEvaluator:
    def __init__(self, df: pd.DataFrame, folds=3):
        self.df = df
        self.folds = folds
        self.engine = BacktestEngine(df)

    def evaluate(self, strategy: StrategyConfig, instrument_type='EQUITY'):
        """
        Performs walk-forward evaluation.
        We split data into N folds.
        Usually WF involves optimizing on In-Sample and testing on Out-of-Sample.
        Since we are *evaluating* a generated strategy (fixed params), we treat the folds as multiple OOS tests?
        Or do we just want to see consistency across time?

        The requirement says: "3–5 folds... Ranking uses OUT-OF-SAMPLE metrics only."

        If strategy parameters are fixed (generated), the whole history is effectively OOS if we didn't train on it.
        But we generated 50 candidates. We pick the best. That IS training (selection bias).

        So we should split data:
        Fold 1: Train (Generate/Select) | Test
        Fold 2: ...

        But the "Generator" generates random parameters.
        So the standard approach here is:
        1. Split data into N chunks.
        2. For each strategy:
           - Run on all chunks?

        Actually, usually "Walk Forward" implies re-optimization.
        Here we have "Self-generating strategy lab".

        Let's interpret "Walk-forward evaluation" for fixed strategies as "K-Fold Cross Validation"
        or simply splitting time into blocks to measure stability.

        However, to prevent overfitting the "Selection" process:
        We should rank based on the OOS portion of the folds?

        Let's assume "Anchored Walk Forward":
        Train on [0..T], Test on [T..T+k].
        Expand window.

        But since we generate random strategies, we can just evaluate them on the *entire* history
        BUT split the history into "IS" and "OOS" segments for the sake of the 'Ranking' score.

        Or better:
        Split history into N blocks.
        Block 1..N-1: In Sample (Used to pass basic filters?)
        Block N: Out of Sample (Used for ranking?)

        The requirement says: "Ranking uses OUT-OF-SAMPLE metrics only."
        And "3-5 folds".

        Let's implement a simple K-Fold time-series split.
        We will return metrics for each fold.
        And the caller (Ranker) will decide how to aggregate (e.g. average OOS scores).

        Actually, "Walk Forward" usually means:
        Train 2020, Test 2021.
        Train 2020-2021, Test 2022.

        Since we are not optimizing parameters of a *specific* strategy logic but picking *random* strategies:
        The "Train" phase is implicitly "Did this strategy survive the filter on IS data?".

        Let's do this:
        Divide data into Folds.
        For each fold:
           Run Backtest.
           Collect Metrics.

        The "OOS" metrics usually refer to the test segments concatenated, or average of test segments.

        Let's simply run backtest on the *entire* period, but also compute metrics for sub-periods (folds).
        This allows the ranker to say "It performed well in 2023, 2024, and 2025".

        If we strictly separate IS/OOS:
        We could say: First 70% is IS. Last 30% is OOS.

        Let's implement `evaluate` returning a list of metrics for each fold.
        We split the dataframe into `self.folds` equal chunks.
        """
        n = len(self.df)
        chunk_size = n // self.folds

        fold_metrics = []

        for i in range(self.folds):
            start = i * chunk_size
            end = (i + 1) * chunk_size if i < self.folds - 1 else n

            sub_df = self.df.iloc[start:end].copy() # Copy to avoid SettingWithCopy

            # Need to handle indicators warmup?
            # Engine will compute indicators on sub_df.
            # This resets indicators (EMA etc) at start of each fold.
            # This is strict/conservative (good).

            engine = BacktestEngine(sub_df, initial_capital=self.engine.initial_capital)
            res = engine.run(strategy, instrument_type)

            m = MetricsCalculator.calculate(res['equity_curve'], res['trades'])
            m['start_date'] = sub_df['datetime'].iloc[0]
            m['end_date'] = sub_df['datetime'].iloc[-1]
            fold_metrics.append(m)

        return fold_metrics

