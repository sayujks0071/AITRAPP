import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Any
from ..factory.grammar import Strategy
from .engine import BacktestEngine
from .metrics import calculate_metrics
import structlog

logger = structlog.get_logger(__name__)

class WalkForwardEvaluator:
    def __init__(self, folds: int = 4):
        self.folds = folds
        self.engine = BacktestEngine()

    def evaluate(self, strategy: Strategy, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Run Walk-Forward Analysis.
        Returns aggregated OOS metrics.
        """
        n = len(df)
        if n < 500: # Need enough data
            return {"valid": False, "reason": "Insufficient data"}

        fold_size = n // (self.folds + 1)

        oos_trades = []
        oos_equity = []

        fold_metrics = []

        # We use expanding window for training (not used for selection here, but for concept)
        # Actually, for strategy evaluation, we just run the strategy on the OOS chunks.
        # Since the strategy params are FIXED (we are evaluating a candidate),
        # we don't need to re-optimize. We just test on OOS folds.
        # So we can just backtest the whole period?
        #
        # Wait, usually WF is: Train on T1, Test on T2. Train on T1+T2, Test on T3.
        # But here we generate candidates with fixed params.
        # The purpose of WF here is to check stability across time.
        # So we just segment the backtest and check metrics per fold.
        # Or better: "Validation" is simply checking if it works on recent unseen data?
        # The prompt says: "Walk-forward evaluation: 3-5 folds... Ranking uses OUT-OF-SAMPLE metrics only."
        # This implies we might be optimizing? But the generator creates fixed candidates.
        #
        # Interpretation: We treat the entire history as a series of folds.
        # A "Candidate" is generated. We check its performance on the "OOS" parts.
        # But if we didn't optimize on the "In-Sample", then everything is "Out-of-Sample"?
        #
        # Ah, maybe the "Generation" step is the "Training"? No, generation is random.
        #
        # Let's interpret "Walk-Forward" here as:
        # Split data into N folds.
        # Run backtest on each fold.
        # Verify consistency.
        #
        # OR, maybe we split into Train/Test. We filter candidates based on Train, then Rank on Test?
        # The prompt says "Ranking uses OUT-OF-SAMPLE metrics only".
        #
        # Let's do this:
        # Split data into Folds.
        # Calculate metrics for each fold.
        # Aggregate metrics (e.g. mean Sharpe).
        # Also check consistency (how many folds positive).

        # Indices for folds
        # Fold 1: 0 to size
        # Fold 2: size to 2*size ...

        full_positions = strategy.generate_positions(df)
        full_positions = strategy.apply_risk_overlay(df, full_positions)

        # Run full backtest first to get trades
        full_res = self.engine.run(df, full_positions)
        full_trades = full_res['trades']
        full_equity = full_res['equity_curve']

        # Now slice results by time to simulate folds
        # This is more efficient than re-running engine

        start_date = df.index[0]
        end_date = df.index[-1]
        total_days = (end_date - start_date).days
        fold_days = total_days // self.folds

        positive_folds = 0
        fold_sharpes = []

        for i in range(self.folds):
            f_start = start_date + pd.Timedelta(days=i*fold_days)
            f_end = start_date + pd.Timedelta(days=(i+1)*fold_days)
            if i == self.folds - 1:
                f_end = end_date

            # Filter trades in this period
            # Trade entry date in period
            f_trades = [t for t in full_trades if f_start <= t.entry_date < f_end]

            if not f_trades:
                fold_sharpes.append(0.0)
                continue

            # Slice equity curve
            # Reconstruct equity curve for this fold?
            # Or just use trade stats.
            # Metrics need equity curve for Sharpe.
            # Let's approximate equity curve from trades for the fold.

            f_pnl = pd.Series([t.pnl for t in f_trades])
            f_returns = pd.Series([t.return_pct for t in f_trades])

            # Approx Sharpe from trade returns (assuming flat time between trades is 0 return? No, that's wrong)
            # Better to slice the main equity curve and rebase it.
            f_equity = full_equity[f_start:f_end]
            if f_equity.empty:
                fold_sharpes.append(0.0)
                continue

            # Rebase
            f_equity = f_equity / f_equity.iloc[0]

            m = calculate_metrics(f_equity, f_trades)
            fold_sharpes.append(m['sharpe'])
            if m['cagr'] > 0:
                positive_folds += 1

        # Overall OOS metrics (last fold? or average?)
        # "Ranking uses OUT-OF-SAMPLE metrics only"
        # If we treat the LAST fold as OOS and others as IS?
        # Or if we treat ALL as OOS because we didn't optimize?
        # Let's treat the LAST fold as the "Pure OOS" for strict ranking,
        # OR use the average of all folds if we consider random generation as "no training".
        #
        # Given "Self-generating strategy lab", usually we want to see if it holds up.
        # Let's calculate metrics on the WHOLE period (since we didn't train),
        # BUT enforce consistency across folds.
        #
        # Wait, "Sanity rejection: OOS folds: at least 2 positive".
        # This implies multiple OOS folds.
        #
        # Let's return the Full Metrics, plus Fold stats.

        full_metrics = calculate_metrics(full_equity, full_trades)

        # Stability: Dispersion of fold sharpes
        stability = 1.0 / (np.std(fold_sharpes) + 0.1) # Higher is better

        full_metrics.update({
            "positive_folds": positive_folds,
            "min_fold_sharpe": min(fold_sharpes) if fold_sharpes else 0.0,
            "stability_score": stability,
            "fold_sharpes": fold_sharpes
        })

        return full_metrics
