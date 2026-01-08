
import pytest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.metrics import calculate_metrics

def test_metrics():
    # Mock Curve
    dates = pd.date_range("2023-01-01", periods=252)
    # 10% return linear
    equity = pd.Series(np.linspace(100000, 110000, 252), index=dates)

    m = calculate_metrics(equity, pd.DataFrame())

    assert m["cagr"] > 0
    assert m["sharpe"] > 0 # No vol? Wait, linspace has vol?
    # Linspace diff is constant. Returns (diff/prev) decreases slightly.
    # Std dev > 0.

    assert m["max_dd"] == 0.0 # No drawdown
