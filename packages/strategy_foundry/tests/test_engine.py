
import pytest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyCandidate

def test_backtest_simple():
    # Mock Data
    dates = pd.date_range("2023-01-01", periods=100)
    df = pd.DataFrame({
        "open": np.linspace(100, 110, 100),
        "high": np.linspace(101, 111, 100),
        "low": np.linspace(99, 109, 100),
        "close": np.linspace(100, 110, 100) # Uptrend
    }, index=dates)

    # Mock Strategy: Always Long
    # We construct a candidate manually or mock interpreter?
    # Let's use a real candidate but one that likely triggers.
    # EMA Cross 9/20 on trending data should trigger.

    blocks = [
        {"type": "EMA_CROSS", "params": {"fast": 2, "slow": 5}},
        {"type": "ATR_STOP", "params": {"period": 5, "multiplier": 10}}
    ]
    cand = StrategyCandidate(id="test", blocks=blocks)

    engine = BacktestEngine()
    res = engine.run(df, cand)

    assert "equity_curve" in res
    assert "trades" in res
    # Should have trades
    # Trend is monotonic, so EMA fast > EMA slow eventually.

    # Check metrics
    # If it buys, equity should go up (100 -> 110)
    # But costs apply.
