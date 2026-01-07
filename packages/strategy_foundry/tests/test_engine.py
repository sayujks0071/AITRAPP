import pandas as pd
import numpy as np
import pytest
from packages.strategy_foundry.backtest.engine import BacktestEngine

def test_backtest_simple_long():
    # Create dummy data
    dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
    df = pd.DataFrame({
        "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        "high": [105] * 10,
        "low": [95] * 10,
        "close": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
        "atr": [1] * 10
    }, index=dates)

    # Signal at index 0 (Day 1) to Buy.
    # Should execute at Day 2 Open (101).
    positions = pd.Series([1] * 10, index=dates) # Always long

    engine = BacktestEngine(initial_capital=10000, slippage_bps=0)
    res = engine.run(df, positions)

    trades = res['trades']
    assert len(trades) > 0
    # First trade entry should be at index 1 date, price 101.
    assert trades[0].entry_price == 101
    assert trades[0].entry_date == dates[1]

    # It should hold until end
    assert trades[-1].exit_reason == "EOD_FORCE"
    assert trades[-1].exit_price == 110

def test_backtest_reversal():
    dates = pd.date_range(start="2023-01-01", periods=5, freq="D")
    # Day 0: Signal 1
    # Day 1: Exec Buy @ 100. Signal -1.
    # Day 2: Exec Sell/Short @ 100. Signal -1.
    # Day 3: Hold Short.

    df = pd.DataFrame({
        "open": [100]*5,
        "high": [101]*5,
        "low": [99]*5,
        "close": [100]*5,
        "atr": [1]*5
    }, index=dates)

    positions = pd.Series([1, -1, -1, -1, -1], index=dates)

    engine = BacktestEngine(initial_capital=10000, slippage_bps=0)
    res = engine.run(df, positions)

    # Trade 1: Buy Day 1 Open, Exit Day 2 Open
    # Trade 2: Short Day 2 Open, Exit Day 4 Close (EOD)

    trades = res['trades']
    assert len(trades) == 2
    assert trades[0].side == 1
    assert trades[0].entry_date == dates[1]
    assert trades[0].exit_date == dates[2]

    assert trades[1].side == -1
    assert trades[1].entry_date == dates[2]
    assert trades[1].exit_date == dates[4]
