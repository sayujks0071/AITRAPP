import pandas as pd
import numpy as np
from typing import Dict, Any, List
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.backtest.metrics import calculate_metrics

def walk_forward_evaluate(engine, strategy: StrategyCandidate, df: pd.DataFrame, folds: int = 3) -> Dict[str, Any]:
    """
    Perform Walk-Forward Analysis.
    Returns aggregated OOS metrics and full OOS equity curve.
    """
    n = len(df)
    if n < 500: # Insufficient data for WF
        return {"metrics": {}, "passed": False, "reason": "Insufficient Data"}

    # Split into folds + 1 segments (1st is initial train, rest are test)
    segment_size = n // (folds + 1)

    oos_trades = []
    oos_equity = []

    # We want to stitch OOS equity.
    # Starts at initial capital.
    current_capital = engine.initial_capital

    fold_metrics = []

    for i in range(folds):
        # Train End / Test Start
        split_idx = segment_size * (i + 1)
        # Test End
        end_idx = segment_size * (i + 2) if i < folds - 1 else n

        # We don't optimize parameters here (Self-Generating Strategy usually generates static params).
        # So we just run the strategy on the Test segment.
        # Why WF then? To verify stability across different regimes.
        # If parameters were optimized, we'd optimize on Train, then run on Test.
        # Here, the candidate has FIXED params.
        # So WF here is just "Out of Sample Performance Validation" across time blocks.
        # Effectively, we are just backtesting on the whole period, but user wants WF structure.
        # Maybe to check "Stability: rolling Sharpe dispersion"?
        # Or to ensure we don't pick a strategy that only worked in the first half?
        # Yes, we use OOS metrics.
        # Since params are fixed, "Train" phase is skipped (we assume the strategy IS the trained model).
        # We just evaluate on the segments.

        test_df = df.iloc[split_idx:end_idx]

        # We need to preserve capital flow?
        # Or reset capital per fold?
        # To make "OOS Equity Curve", we should preserve.
        # But engine takes initial_capital.
        # We can update engine capital or stitch returns.

        # Create a temporary engine instance or update capital
        # Wait, if we just run on the whole DF, we get the same result as stitching fixed param runs.
        # UNLESS the requirement implies we should be OPTIMIZING params on Train?
        # "Implement new research components ... strategy grammar/generator ... parameter_space".
        # "Self-generating strategy lab".
        # Usually: Generate Candidates -> Filter -> Select.
        # The Candidates are generated with random params.
        # So they are not "trained" on data yet.
        # If we evaluate them on the whole history, we overfit.
        # Ah!
        # Evaluation should be:
        # 1. Generate on Training Data? NO, the generator is random.
        # 2. Rank based on OOS?
        # If we use ALL data to select the best, we overfit.
        # The "Walk-Forward" usually implies:
        # Train on A, Select Best, Test on B.
        # Repeat.
        # But here we are processing ONE candidate.
        # If the candidate is generated randomly, it has no bias to any period.
        # EXCEPT if we select it based on its performance on the WHOLE period.
        # User says: "Ranking uses OUT-OF-SAMPLE metrics only."
        # This implies we must split data.
        # But if we don't optimize, what is In-Sample?
        # Maybe we treat the *Selection* as the training.
        # But for a single candidate, "OOS metrics" usually means "Metrics on the Test Folds".
        # If we just calculate metrics on the whole DF, isn't that OOS if the generator didn't see the data?
        # Yes, technically.
        # BUT, "Walk-forward evaluation: 3-5 folds".
        # This explicitly asks for the fold structure.
        # Perhaps to measure *consistency*.
        # "OOS folds: at least 2 positive".
        # This means we check performance in each fold.

        # So, we simply split the data into K segments (folds) and verify it works in most of them.
        # We can treat the *entire* history as a series of OOS blocks (since we didn't train on any).
        # Or we skip the first block?
        # User says "Ranking uses OUT-OF-SAMPLE metrics only".
        # If we skip the first block, we lose data.
        # But "Walk-forward" implies a time progression.
        # Let's assume we use the last K blocks as OOS folds.
        # "3-5 folds".
        # I will split data into equal chunks and run backtest on each.
        # I will aggregate the metrics.

        engine.initial_capital = current_capital
        result = engine.run(strategy, test_df)

        trades = result["trades"]
        equity = result["equity_curve"]
        metrics = result["metrics"]

        if not trades.empty:
            oos_trades.extend(trades.to_dict("records"))

        # Stitch equity
        # The engine equity curve starts at current_capital.
        # We append it.
        # Need to handle index alignment if we want a full series.
        # result["equity_curve"] has the correct dates.
        if i == 0:
             oos_equity.append(equity)
        else:
             oos_equity.append(equity) # Overlap? No, indices are distinct.

        current_capital = equity.iloc[-1]

        # Check pass criteria for this fold
        fold_passed = metrics["total_return"] > 0
        fold_metrics.append({
            "fold": i,
            "return": metrics["total_return"],
            "sharpe": metrics["sharpe"],
            "passed": fold_passed
        })

    # Aggregate
    if not oos_trades:
        return {"metrics": {}, "passed": False, "reason": "No Trades"}

    full_equity = pd.concat(oos_equity)
    agg_metrics = calculate_metrics(oos_trades, full_equity)

    # Stability
    # "rolling 252D Sharpe dispersion"
    # We can compute this on full_equity
    returns = full_equity.pct_change().dropna()
    rolling_sharpe = returns.rolling(252).apply(lambda x: (x.mean() / x.std() * np.sqrt(252)) if x.std() > 0 else 0)
    stability = 1.0 / (rolling_sharpe.std() + 1e-6) # Higher is better? Or just return std.
    sharpe_std = rolling_sharpe.std()

    # Sanity Rejection Logic here or outside?
    # "at least 2 positive folds"
    positive_folds = sum(1 for f in fold_metrics if f["passed"])
    passed_folds = positive_folds >= (folds / 2) # Rough heuristic or strict "2"
    if positive_folds < 2 and folds >= 3:
         passed_folds = False

    return {
        "metrics": agg_metrics,
        "fold_metrics": fold_metrics,
        "stability_metric": sharpe_std,
        "equity_curve": full_equity,
        "positive_folds": positive_folds,
        "passed_folds": passed_folds
    }
