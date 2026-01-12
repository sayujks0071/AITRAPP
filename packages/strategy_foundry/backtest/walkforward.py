import pandas as pd
import numpy as np
from typing import Dict, Any, List
from packages.strategy_foundry.backtest.engine import Engine

def walk_forward_validation(
    data: pd.DataFrame,
    strategy_factory_func,
    n_folds: int = 3,
    train_size_days: int = 365*2,
    test_size_days: int = 180
) -> Dict[str, Any]:
    """
    Perform Walk-Forward Validation.
    strategy_factory_func: function that takes data and returns signals (or positions).
    """
    # Define Folds
    # We want latest data to be in test?
    # Or strict rolling?
    # "Expanding window for training and rolling window for testing" per memory.

    # Let's verify data length
    total_days = (data.index[-1] - data.index[0]).days
    if total_days < train_size_days + test_size_days:
        return {"error": "Not enough data"}

    results = []

    # We iterate backwards from end? Or forwards?
    # Usually forwards to simulate history.

    # Determine start point
    # We need at least train_size_days
    start_idx = 0
    # Find index for start_date + train_size

    # Let's slice by index logic
    # Make folds
    # Fold 1: Train [Start, Start+Train], Test [Start+Train, Start+Train+Test]
    # Fold 2: Train [Start, Start+Train+Test], Test [Start+Train+Test, Start+Train+2*Test] (Expanding)

    # But we want 'n_folds'.
    # Let's work backwards from end.

    test_starts = []
    end_date = data.index[-1]

    current_end = end_date
    for _ in range(n_folds):
        test_start = current_end - pd.Timedelta(days=test_size_days)
        if test_start < data.index[0] + pd.Timedelta(days=train_size_days):
            break
        test_starts.append(test_start)
        current_end = test_start

    test_starts.reverse() # Chronological

    aggregate_metrics = {
        "sharpe_sum": 0,
        "calmar_sum": 0,
        "cagr_sum": 0,
        "positive_folds": 0,
        "folds": 0
    }

    equity_curves = []

    for t_start in test_starts:
        # Train Data
        # Expanding window: Start of data -> t_start
        train_end = t_start
        train_data = data[data.index < train_end]

        # Test Data
        test_end = t_start + pd.Timedelta(days=test_size_days)
        test_data = data[(data.index >= t_start) & (data.index < test_end)]

        if test_data.empty:
            continue

        # Run Strategy on Test Data?
        # Strategy typically needs lookback (indicators).
        # So we must pass (Train + Test) to indicator calc, then slice signals?
        # Or pass full data, generate signals, then slice backtest?
        # Much safer to generate signals on full data (or window) then slice result.
        # But to avoid lookahead, we must ensure Strategy doesn't use future.
        # Our indicators are causal.

        # Generate Signals on Combined Data (to warm up indicators)
        # We need some warmup from train for test indicators.
        warmup_days = 365
        warmup_start = t_start - pd.Timedelta(days=warmup_days)
        run_data = data[(data.index >= warmup_start) & (data.index < test_end)]

        # Call factory (generates positions)
        signals = strategy_factory_func(run_data)

        # Slice signals for Test Period
        test_signals = signals[signals.index >= t_start]

        # Backtest Test Period
        # We execute strictly on test_signals.
        # Initial capital 100k
        engine = Engine(test_data)
        res = engine.run(test_signals)

        results.append(res.stats)
        aggregate_metrics["folds"] += 1
        aggregate_metrics["sharpe_sum"] += res.stats.get("sharpe", 0)
        aggregate_metrics["calmar_sum"] += (res.stats.get("cagr", 0) / res.stats.get("max_drawdown", 1)) if res.stats.get("max_drawdown", 0) > 0 else 0
        aggregate_metrics["cagr_sum"] += res.stats.get("cagr", 0)

        if res.stats.get("total_return", 0) > 0:
            aggregate_metrics["positive_folds"] += 1

        equity_curves.append(res.equity_curve)

    # Average metrics
    n = aggregate_metrics["folds"]
    if n > 0:
        avg_stats = {
            "avg_sharpe": aggregate_metrics["sharpe_sum"] / n,
            "avg_calmar": aggregate_metrics["calmar_sum"] / n, # Approximate
            "avg_cagr": aggregate_metrics["cagr_sum"] / n,
            "positive_fold_ratio": aggregate_metrics["positive_folds"] / n
        }
    else:
        avg_stats = {}

    return {
        "fold_results": results,
        "avg_stats": avg_stats
    }
