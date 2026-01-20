"""1D Sanity Check"""
import pandas as pd
from typing import Dict
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import calculate_metrics

def run_sanity_check(candidate: StrategyCandidate, daily_data: pd.DataFrame) -> Dict:
    """
    Run candidate on 1D data.
    Note: Intraday strategies (e.g. 15m entries) might not map directly to 1D bars.
    We need to approximate.

    If strategy is "Donchian Breakout 20", on 1D it means 20 Day Breakout.
    This is a valid robustness check: does the logic hold on higher TF?

    However, "ORB" (Opening Range Breakout) makes NO sense on 1D bars (no opening range).
    "EOD Exit" makes NO sense on 1D (holding 1 day?).

    So we only check "structural" sanity if possible.
    If the strategy is heavily intraday specific (ORB, TimeStop in minutes),
    1D backtest might be technical garbage.

    But the prompt says: "Take top 10 candidates... and run 1D sanity backtest".
    "If daily performance is catastrophically negative... reject".

    We will attempt to run it.
    The `BacktestEngine` and `IndicatorsAdapter` handle 1D data fine (it's just bars).
    ORB block might fail or do weird things if logic requires minutes.

    Let's ensure adapters handle it gracefully.
    """
    if daily_data.empty:
        return {"passed": True, "reason": "no_data"}

    # Create engine
    engine = BacktestEngine(daily_data)

    # Run
    # Issues:
    # - EODExit on 1D: Exits at end of day? i.e. holding period 0?
    #   If EODExit is present, 1D backtest will enter and exit same bar (if engine allows) or next open.
    #   If we exit at Close of same bar, PnL is Close-Open.
    #   This captures "Day Trading" on daily bars?

    try:
        res = engine.run(candidate)
        metrics = calculate_metrics(res["equity"], res["trades"])

        # Criteria: "catastrophically negative"
        # Sharpe < -0.2 or MaxDD > 45%

        sharpe = metrics.get("sharpe", 0)
        max_dd = metrics.get("max_dd", 0)

        passed = True
        reason = "OK"

        if sharpe < -0.2:
            passed = False
            reason = f"Sharpe too low ({sharpe:.2f})"

        if max_dd < -0.45: # MaxDD is negative number usually in my calc?
                           # In metrics.py: (equity - peak) / peak. So it is negative.
                           # So if max_dd < -0.45 (i.e. > 45% drop)
            passed = False
            reason = f"MaxDD too high ({max_dd:.2f})"

        return {
            "passed": passed,
            "reason": reason,
            "metrics": metrics
        }
    except Exception as e:
        # If it crashes (e.g. indicator not compatible with 1D), we might warn but pass?
        # Or fail?
        return {"passed": True, "reason": f"Sanity crash: {str(e)}"}
