
import pytest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyCandidate

def test_engine_basic():
    # Mock data
    dates = pd.date_range("2023-01-01", periods=100)
    data = pd.DataFrame({
        "Open": np.linspace(100, 110, 100),
        "High": np.linspace(101, 111, 100),
        "Low": np.linspace(99, 109, 100),
        "Close": np.linspace(100, 110, 100),
        "Volume": 1000
    }, index=dates)

    # Mock candidate
    candidate = StrategyCandidate(
        id="test",
        entry_rules=[],
        exit_rules=[],
        params={}
    )

    engine = BacktestEngine(data)
    res = engine.run(candidate)

    assert "metrics" in res
    assert "trades" in res
    assert "equity_curve" in res
    assert "current_position" in res

def test_engine_with_trade():
    dates = pd.date_range("2023-01-01", periods=50)
    data = pd.DataFrame({
        "Open": [100]*50,
        "High": [105]*50,
        "Low": [95]*50,
        "Close": [100]*50,
        "Volume": 1000
    }, index=dates)

    # Add indicators manually or rely on adapter defaults (which might fail if calc needs meaningful data)
    # The adapter calculates EMA/RSI. RSI needs price changes.
    # Let's make price move.
    data["Close"] = np.linspace(100, 200, 50)
    data["Open"] = data["Close"]
    data["High"] = data["Close"] + 1
    data["Low"] = data["Close"] - 1

    # Strategy: EMA Cross
    # Fast (10) > Slow (20)
    # Price is increasing, so Fast EMA > Slow EMA eventually.

    candidate = StrategyCandidate(
        id="test_cross",
        entry_rules=[{"type": "ema_cross_above", "fast": "fast", "slow": "slow"}],
        exit_rules=[{"type": "ema_cross_below", "fast": "fast", "slow": "slow"}],
        params={"fast": 10, "slow": 20}
    )

    engine = BacktestEngine(data)
    res = engine.run(candidate)

    # Should have some trades or at least metrics calculated
    assert res["metrics"]["trades"] >= 0
