import pandas as pd
import numpy as np
from datetime import datetime
import pytest
from packages.strategy_foundry.backtest.metrics import calculate_metrics

def test_metrics_calculation():
    # 1. Profitable case
    trades = [
        {"entry_time": pd.Timestamp("2023-01-01"), "exit_time": pd.Timestamp("2023-01-02"), "return": 0.01},
        {"entry_time": pd.Timestamp("2023-01-03"), "exit_time": pd.Timestamp("2023-01-04"), "return": 0.005},
        {"entry_time": pd.Timestamp("2023-01-05"), "exit_time": pd.Timestamp("2023-01-06"), "return": -0.002},
    ]

    dates = pd.date_range("2023-01-01", "2023-01-10", freq="D")
    # Simulate equity curve
    equity_curve = pd.Series(index=dates, data=1.0)
    equity_curve.loc["2023-01-02":] = 1.01
    equity_curve.loc["2023-01-04":] = 1.015
    equity_curve.loc["2023-01-06":] = 1.013

    metrics = calculate_metrics(trades, equity_curve, pd.DataFrame())

    assert metrics["trades"] == 3
    assert metrics["win_rate"] == 2/3
    assert metrics["profit_factor"] > 1.0
    assert metrics["cagr"] > 0
    assert metrics["sharpe"] > 0

def test_metrics_empty():
    metrics = calculate_metrics([], pd.Series([1.0]), pd.DataFrame())
    assert metrics["trades"] == 0
    assert metrics["sharpe"] == 0.0
