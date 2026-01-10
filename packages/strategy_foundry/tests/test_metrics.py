import pandas as pd
import numpy as np
from datetime import datetime
import pytest
from packages.strategy_foundry.backtest.metrics import calculate_metrics

def test_metrics_calculation():
    # 1. Profitable case
    trades = pd.DataFrame([
        {"entry_time": pd.Timestamp("2023-01-01"), "exit_time": pd.Timestamp("2023-01-02"), "pnl": 100},
        {"entry_time": pd.Timestamp("2023-01-03"), "exit_time": pd.Timestamp("2023-01-04"), "pnl": 50},
        {"entry_time": pd.Timestamp("2023-01-05"), "exit_time": pd.Timestamp("2023-01-06"), "pnl": -20},
    ])

    dates = pd.date_range("2023-01-01", "2023-01-10", freq="D")
    equity_curve = pd.Series(index=dates, data=100000)
    equity_curve.loc["2023-01-02":] = 100100
    equity_curve.loc["2023-01-04":] = 100150
    equity_curve.loc["2023-01-06":] = 100130

    metrics = calculate_metrics(trades, equity_curve, 100000)

    assert metrics["trades"] == 3
    assert metrics["win_rate"] == 2/3
    assert metrics["profit_factor"] == 150 / 20
    assert metrics["cagr"] > 0
    assert metrics["sharpe"] > 0

def test_metrics_empty():
    metrics = calculate_metrics(pd.DataFrame(), pd.Series(dtype=float))
    assert metrics["trades"] == 0
    assert metrics["sharpe"] == 0.0

def test_metrics_loss():
    trades = pd.DataFrame([
        {"entry_time": pd.Timestamp("2023-01-01"), "exit_time": pd.Timestamp("2023-01-02"), "pnl": -100},
    ])
    equity_curve = pd.Series([100000, 99900], index=pd.date_range("2023-01-01", periods=2))

    metrics = calculate_metrics(trades, equity_curve, 100000)
    assert metrics["profit_factor"] == 0.0
    assert metrics["max_dd"] > 0
