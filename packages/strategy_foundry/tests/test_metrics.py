
import pytest
import pandas as pd
from packages.strategy_foundry.backtest.metrics import compute_metrics

def test_metrics():
    equity = pd.Series([100, 110, 105, 120], index=pd.date_range("2023-01-01", periods=4))
    trades = pd.DataFrame([
        {"return": 0.1},
        {"return": -0.05},
        {"return": 0.15}
    ])

    m = compute_metrics(equity, trades)
    assert "cagr" in m
    assert "sharpe" in m
    assert m["trades"] == 3
