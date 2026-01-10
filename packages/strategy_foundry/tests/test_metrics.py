
import pytest
import pandas as pd
from packages.strategy_foundry.backtest.metrics import calculate_metrics

def test_metrics():
    # Scenario: 2 trades, one win, one loss
    trades = [
        {"pnl": 1000},
        {"pnl": -500}
    ]
    # Equity curve: 100k -> 101k -> 100.5k
    dates = pd.date_range("2023-01-01", periods=3)
    equity = pd.Series([100000, 101000, 100500], index=dates)

    m = calculate_metrics(equity, trades)

    assert m["total_trades"] == 2
    assert m["win_rate"] == 0.5
    assert m["max_dd"] < 0 # -0.0049... (100.5/101 - 1)
