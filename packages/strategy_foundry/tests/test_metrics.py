import pytest
import pandas as pd
from packages.strategy_foundry.backtest.metrics import calculate_metrics

def test_metrics_empty():
    df = pd.DataFrame()
    m = calculate_metrics(df)
    assert m["total_return"] == 0.0

def test_metrics_basic():
    trades = pd.DataFrame({
        "entry_time": [pd.Timestamp("2023-01-01"), pd.Timestamp("2023-02-01")],
        "exit_time": [pd.Timestamp("2023-01-10"), pd.Timestamp("2023-02-10")],
        "return_pct": [0.05, -0.02]
    })

    m = calculate_metrics(trades)
    assert m["trades"] == 2
    assert m["total_return"] > 0
    assert m["win_rate"] == 0.5
