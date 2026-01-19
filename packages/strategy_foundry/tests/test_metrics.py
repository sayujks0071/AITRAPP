import pytest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.metrics import calculate_metrics

def test_metrics_calculation():
    dates = pd.date_range("2023-01-01", periods=252)
    # 10% annual return
    equity = pd.Series(np.linspace(100, 110, 252), index=dates)

    trades = pd.DataFrame({
        "pnl": [5, -2, 5, 2],
        "return_pct": [0.05, -0.02, 0.05, 0.02]
    })

    metrics = calculate_metrics(equity, trades)

    assert metrics["total_return"] == 0.1
    assert metrics["cagr"] > 0
    assert metrics["trades"] == 4
    assert metrics["win_rate"] == 0.75 # 3 wins, 1 loss
    assert metrics["max_drawdown"] <= 0 # Should be negative or zero (here 0 because monotonic up)

def test_metrics_empty():
    m = calculate_metrics(pd.Series(), pd.DataFrame())
    assert m == {}
