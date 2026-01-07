import pandas as pd
import pytest
from packages.strategy_foundry.backtest.metrics import calculate_metrics
from packages.strategy_foundry.backtest.engine import Trade

def test_metrics_empty():
    res = calculate_metrics(pd.Series(), [])
    assert res['cagr'] == 0.0
    assert res['sharpe'] == 0.0

def test_metrics_simple():
    dates = pd.date_range(start="2023-01-01", periods=5)
    equity = pd.Series([100, 101, 102, 103, 104], index=dates)

    trades = [
        Trade(dates[0], 100, dates[1], 101, 1, 1, 1.0, 0.01, "", "")
    ]

    res = calculate_metrics(equity, trades)
    assert res['cagr'] > 0
    assert res['trades'] == 1
    assert res['win_rate'] == 1.0
