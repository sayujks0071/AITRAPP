"""Walk-forward analysis"""
import pandas as pd
from typing import List, Dict, Tuple
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class WalkForwardAnalyst:
    def __init__(self, engine: BacktestEngine, folds: int = 4):
        self.engine = engine
        self.folds = folds

    def run(self, candidate: StrategyCandidate, data: pd.DataFrame) -> Dict:
        """
        Run Walk-Forward Analysis.

        Splits data into K folds.
        For each fold:
           Train (Expanding Window or Rolling?)
           Test (Next chunk)

        We use Expanding Window for Train, Rolling for Test.
        Actually, for strategy generation (ranking), we just want OOS performance.
        We are NOT optimizing params here (that would require optimization loop).
        The candidate HAS fixed params.
        So we just run it on the chunks and aggregate OOS results.

        If params are fixed, "Walk Forward" is just "Cross Validation" or simply running on OOS chunks.
        Wait, if we generated random params, we assume they are "fitted" to... nothing yet?
        Ah, usually Foundry generates params, then checks performance.
        If we check performance on WHOLE history, we overfit.

        Correct Approach for "Self-Generating":
        1. Generate Candidate (with random params).
        2. Evaluate on Fold 1 (Train). If good, Keep?
        3. No, we want to see STABILITY.

        Actually, the requirement says "Rank with strong anti-overfit gates" and "Use walk-forward OOS evaluation".
        And "Train results may be logged but not used for score".

        So we split data into K segments.
        We run the FIXED candidate on each Test segment.
        But where did the params come from? Random.
        So effectively we are treating the "Training" phase as implicit (random search).
        We just want to measure performance on OOS folds.

        If we treat the entire history as OOS (since we didn't train on it), that's one way.
        But to simulate "robustness over time", we can split into K blocks and see if it passes > X folds.

        Implementation:
        Split data into `folds` equal chunks.
        Run backtest on each chunk.
        Collect metrics for each chunk.
        Aggregate.
        """
        if data.empty:
            return {"oos_score": -999}

        chunk_size = len(data) // self.folds
        if chunk_size < 100: # Too small
            return {"oos_score": -999}

        fold_results = []
        equity_curves = []
        all_trades = []

        for i in range(self.folds):
            start = i * chunk_size
            end = (i + 1) * chunk_size if i < self.folds - 1 else len(data)

            fold_data = data.iloc[start:end]
            eq, trades = self.engine.run_safe(candidate, fold_data)

            m = calculate_metrics(trades, eq)
            m["fold"] = i
            fold_results.append(m)
            equity_curves.append(eq)
            all_trades.extend(trades)

        # Aggregate OOS Metrics (Average of folds? or Concatenated equity?)
        # Better to concatenate trades and calc global OOS metrics,
        # BUT check consistency across folds.

        # 1. Global OOS Metrics (concatenating all OOS segments = full run effectively, but we analyze fold consistency)
        # Since we didn't train, the whole set is OOS.
        # But we need to ensure it wasn't just lucky in one month.

        positive_folds = sum(1 for f in fold_results if f["net_profit"] > 0)

        # Calculate consistency score
        sharpes = [f["sharpe"] for f in fold_results]
        avg_sharpe = sum(sharpes) / len(sharpes)
        sharpe_std = pd.Series(sharpes).std() if len(sharpes) > 1 else 0

        stability = 1.0 / (1.0 + sharpe_std) # Higher is better

        # Global metrics
        global_metrics = calculate_metrics(all_trades, pd.concat(equity_curves))

        return {
            "folds": fold_results,
            "positive_folds": positive_folds,
            "stability_score": stability,
            "global": global_metrics,
            "avg_sharpe": avg_sharpe
        }
