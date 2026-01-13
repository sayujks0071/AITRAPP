from packages.strategy_foundry.backtest.engine import FoundryEngine
import pandas as pd
import numpy as np

def test_engine_metrics():
    engine = FoundryEngine()

    # 10 days
    dates = pd.date_range("2023-01-01", periods=10)
    df = pd.DataFrame({
        "open": [100, 101, 102, 103, 104, 105, 104, 103, 102, 101],
        "close": [100.5, 101.5, 102.5, 103.5, 104.5, 104.5, 103.5, 102.5, 101.5, 100.5],
        "high": [101]*10,
        "low": [99]*10
    }, index=dates)

    # Buy at T=0 (Exec T=1 Open: 101).
    # Sell at T=5 (Exec T=6 Open: 104).
    # Profit: (104 - 101)/101 approx 3%

    positions = pd.Series(0, index=dates)
    positions.iloc[0:5] = 1 # Signal 1 for days 0,1,2,3,4.
    # At day 0 signal 1 -> Day 1 Open enter.
    # At day 4 signal 1 -> Day 5 Open hold.
    # At day 5 signal 0 -> Day 6 Open exit.

    # Expected: Enter 101, Exit 104.

    res = engine.run(df, positions)
    trades = res["trades"]

    assert len(trades) == 1
    assert trades[0].entry_price > 100 # ~101 + slip
    assert trades[0].exit_price < 105 # ~104 - slip
    assert trades[0].pnl > 0

    metrics = engine.calculate_metrics(trades)
    assert metrics["win_rate"] == 1.0
