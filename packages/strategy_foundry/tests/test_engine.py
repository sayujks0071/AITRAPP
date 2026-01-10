
import pytest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import VectorBacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyConfig, Rule

def test_engine_basic():
    # Create synthetic data
    dates = pd.date_range("2023-01-01", periods=100)
    df = pd.DataFrame({
        "open": np.linspace(100, 200, 100),
        "high": np.linspace(101, 201, 100),
        "low": np.linspace(99, 199, 100),
        "close": np.linspace(100, 200, 100), # Constant uptrend
        "volume": 1000
    }, index=dates)

    # Strategy: Trend Follow (EMA Cross)
    # Fast=5, Slow=10. Since price is linear uptrend, Fast > Slow always after warm up.

    strat = StrategyConfig(
        entry_rules=[Rule("EMA_CROSS", {"fast": 5, "slow": 10})],
        exit_rules=[],
        risk_rules=[Rule("ATR_STOP", {"period": 14, "multiplier": 3.0})]
    )

    engine = VectorBacktestEngine()
    res = engine.run(df, strat)

    assert "metrics" in res
    assert "equity_curve" in res

    # Check trades
    trades = res["trades"]

    # With linear uptrend and force close logic:
    # 1. Warm up ~10 bars
    # 2. Enter Long
    # 3. Hold until end (stop never hit)
    # 4. Force Close at last bar

    # We should have exactly 1 trade
    # Or 0 if warmup didn't complete? 100 bars is enough for EMA 10.

    assert len(trades) >= 1

    last_trade = trades[-1]
    assert last_trade["pnl"] > 0 # Should be profitable in uptrend
    assert last_trade["exit_date"] == dates[-1] # Force closed
