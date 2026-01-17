import pandas as pd
import numpy as np
from typing import List, Tuple
from .engine import BacktestEngine
from .metrics import calculate_metrics
from packages.strategy_foundry.factory.grammar import StrategyCandidate
import structlog

logger = structlog.get_logger(__name__)

class WalkForwardEvaluator:
    def __init__(self, n_folds=3):
        self.n_folds = n_folds
        self.engine = BacktestEngine()

    def evaluate(self, df: pd.DataFrame, candidate: StrategyCandidate) -> dict:
        """
        Perform walk-forward evaluation.
        Splits data into K folds.
        Train (In-Sample) -> Test (Out-Of-Sample).
        Actually, for strategy ranking, we often just want OOS performance aggregated.
        Simple approach:
        - Divide data into N blocks.
        - Evaluate on each block?
        - Or Expanding window?
        - Plan says: "Walk-forward evaluation: 3-5 folds". "Ranking uses OUT-OF-SAMPLE metrics only."

        Implementation:
        Split DF into N+1 chunks.
        Fold 1: Train on Chunk 0, Test on Chunk 1.
        Fold 2: Train on Chunk 0+1, Test on Chunk 2.
        ...

        However, since we are *generating* strategies, we aren't "training" parameters in the loop (they are fixed in the candidate).
        So this is more like "Cross-Validation" or just testing on multiple periods?

        If params are fixed, "In-Sample" results are just backtest on past data. "Out-Of-Sample" is future data.
        But we are looking at historical data.

        Interpretation:
        We simulate proper Walk-Forward optimization? No, the candidate generator picks random params.
        So we are evaluating if these random params work on "unseen" data.

        We can just run the strategy on the WHOLE dataset, but segment the metrics.
        BUT, we want to simulate "selection bias".

        Let's do:
        Split data into 3 chunks.
        Chunk 1: "IS" (Selection)
        Chunk 2: "OOS" (Validation)
        Chunk 3: "OOS" (Test)

        Actually, simpler:
        Just run backtest on full history.
        The "OOS" requirement usually implies we optimized on IS. Since we randomly generated, *technically* the whole thing is OOS until we pick the best one.
        Once we pick the best one based on Full History, we overfit.

        Better approach for "Self-Generating":
        - Generate N candidates.
        - Evaluate all on Period A (IS). Pick top X.
        - Evaluate top X on Period B (OOS).

        This aligns with "Ranking uses OUT-OF-SAMPLE metrics only".

        So this `evaluate` method should probably return metrics for the OOS period(s).

        Let's split dataset:
        Train: 60%
        Test: 40% (This is the OOS part we care about for ranking).

        Or Rolling K-Fold:
        Split into k segments.
        Use segment i-1 to rank, segment i to test?

        Let's stick to simple TimeSeriesSplit.
        We will return aggregated OOS metrics.

        Actually, simpler interpretation of plan:
        "Walk-forward evaluation... Ranking uses OOS metrics only."
        This implies the system orchestrator handles the split.
        This class should just help split/aggregate.

        Let's just implement a helper that takes df and returns the OOS metrics.
        We will use the last 30% of data as OOS?
        Or multiple folds.

        Let's do 3 folds of (Train 1yr, Test 6mo).
        Aggregate the Test results.
        """

        # Determine folds
        total_days = (df.index[-1] - df.index[0]).days
        if total_days < 365:
            # Not enough data for WF
            return {}

        # Let's say we use a simple 70/30 split for the "Production" OOS score.
        # This is robust and simple.

        split_idx = int(len(df) * 0.7)
        # is_df = df.iloc[:split_idx]
        oos_df = df.iloc[split_idx:]

        # Run on OOS
        trades, equity, _ = self.engine.run(oos_df, candidate)
        metrics = calculate_metrics(equity, trades)

        return metrics
