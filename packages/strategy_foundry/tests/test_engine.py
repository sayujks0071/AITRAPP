import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytest
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategySpec

@pytest.fixture
def sample_data():
    dates = pd.date_range(start="2023-01-01", periods=100, freq="15min")
    df = pd.DataFrame(index=dates)
    # Generate random walk
    np.random.seed(42)
    returns = np.random.normal(0, 0.001, 100)
    price = 100 * (1 + returns).cumprod()

    df["Close"] = price
    df["Open"] = price * (1 + np.random.normal(0, 0.0005, 100))
    df["High"] = df[["Open", "Close"]].max(axis=1) * 1.001
    df["Low"] = df[["Open", "Close"]].min(axis=1) * 0.999
    df["Volume"] = 1000
    return df

def test_engine_basic(sample_data):
    # Create a dummy strategy
    spec = StrategySpec(
        id="test",
        entry_logic={"type": "Breakout", "period": 10, "confirm_vol": False},
        exit_logic={"stop_type": "FixedPct", "sl_mult": 1.0, "tp_risk_reward": 2.0},
        filters=[],
        timeframe="15m"
    )

    engine = BacktestEngine(sample_data)
    results = engine.run(spec)

    assert "trades" in results
    assert "equity_curve" in results
    assert len(results["equity_curve"]) == len(sample_data)

def test_signal_generation(sample_data):
    # Force a breakout pattern
    # Highs increasing
    sample_data["High"] = range(100, 200)
    sample_data["Close"] = range(100, 200)

    spec = StrategySpec(
        id="test",
        entry_logic={"type": "Breakout", "period": 5, "confirm_vol": False},
        exit_logic={"stop_type": "FixedPct", "sl_mult": 1.0, "tp_risk_reward": 2.0},
        filters=[],
        timeframe="15m"
    )

    engine = BacktestEngine(sample_data)
    # We need to compute indicators first as run() does
    df_ind = engine.indicators.add_all(sample_data)
    signals = engine._generate_signals(df_ind, spec)

    # Should have signals
    assert signals.sum() > 0
