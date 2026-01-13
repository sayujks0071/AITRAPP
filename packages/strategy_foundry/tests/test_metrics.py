import pytest
import pandas as pd
from packages.strategy_foundry.backtest.metrics import calculate_metrics

def test_metrics_empty():
    df = pd.DataFrame()
    equity = [100.0]
    m = calculate_metrics(df, equity)
    assert m["total_trades"] == 0
    assert m["sharpe"] == 0

def test_metrics_basic():
    trades = pd.DataFrame([
        {"pnl_net": 0.05, "entry_time": "2023-01-01"},
        {"pnl_net": -0.02, "entry_time": "2023-01-02"},
        {"pnl_net": 0.03, "entry_time": "2023-01-03"}
    ])
    equity = [100.0, 105.0, 102.9, 105.98]
    m = calculate_metrics(trades, equity)
    assert m["total_trades"] == 3
    assert m["win_rate"] == 2/3
    assert m["net_profit"] > 0
