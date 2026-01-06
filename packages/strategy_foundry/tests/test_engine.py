import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import run_backtest
from packages.strategy_foundry.backtest.metrics import calculate_metrics

def test_backtest_engine_simple():
    # 10 days
    dates = pd.date_range(start="2023-01-01", periods=10)
    # Price goes up 10% every day
    prices = [100 * (1.1 ** i) for i in range(10)]

    df = pd.DataFrame({
        "open": prices,
        "close": prices,
        "high": prices,
        "low": prices
    }, index=dates)

    # Always long
    positions = pd.Series(1, index=dates)

    costs = {'slippage_bps': 0, 'all_in_cost_bps': 0}

    res = run_backtest(df, positions, costs)

    # Expect equity curve to match price roughly (delayed by 1 day entry)
    # Day 0: Signal Long.
    # Day 1: Enter at Open (110). Close is 110. Return 0?
    # Actually if Open=Close, intraday return is 0.
    # Gap return from Day 0 Close (100) to Day 1 Open (110) is missed if we enter at Day 1 Open.
    # So we miss the gaps.

    # If Open == Close, and NextOpen == NextClose (stepwise jumps),
    # OpRet = 0.
    # GapRet = 10%.
    # If we enter at Open Day 1, we miss Gap 0->1.
    # We hold 1->2. We catch Gap 1->2? No.
    # Logic:
    # positions[i-2] determines state entering Gap i.
    # positions[i-1] determines state for Session i.

    # Day 0: pos=1.
    # Day 1: pos_prev (Day-1?) = 0. pos_curr (Day0) = 1.
    # We enter at Open 1. We missed Gap 0->1.
    # Session 1: Held.
    # Gap 1->2: pos_prev(Day0) = 1. We catch Gap.

    # So we should catch returns from Day 2 onwards.

    returns = res['returns']
    assert len(returns) == 10
    # Day 0: NaN or 0
    # Day 1: Entry cost (0). Return 0 (no intraday move).
    # Day 2: Gap return (10%).

    assert returns.iloc[2] > 0.09 # approx 10%

    metrics = calculate_metrics(returns, res['trades'])
    assert metrics['cagr'] > 0
