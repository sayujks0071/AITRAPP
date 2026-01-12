import pytest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import Engine

def test_engine_basic():
    # Create simple data
    dates = pd.date_range("2023-01-01", periods=10)
    data = pd.DataFrame({
        "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        "close": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
    }, index=dates)

    # Signal: Always Long
    signals = pd.Series(1, index=dates)

    engine = Engine(data, initial_capital=10000, slippage_bps=0, cost_bps=0)
    res = engine.run(signals)

    # We enter at Open of Day 2 (index 1) based on Signal Day 1 (index 0).
    # Position day 1 is 0.
    # Position day 2 is 1.

    # Day 1: pos=0. Ret=0.
    # Day 2: pos=1. Gap Ret = (101-101)/101 * 0 = 0. Intra Ret = (102-101)/101 = ~1%.
    # Day 3: pos=1. Gap Ret = (102-102)/102 * 1 = 0. Intra Ret = (103-102)/102.

    # Check Trades
    assert res.stats['trades'] == 1 # Entry at start
    assert res.stats['total_return'] > 0
