import pytest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyCandidate, EntryType, ExitType

@pytest.fixture
def sample_data():
    # Generate 100 bars of dummy data
    dates = pd.date_range("2023-01-01", periods=100, freq="5min")
    df = pd.DataFrame({
        "open": np.linspace(100, 110, 100),
        "high": np.linspace(101, 111, 100),
        "low": np.linspace(99, 109, 100),
        "close": np.linspace(100.5, 110.5, 100),
        "volume": 1000
    }, index=dates)
    return df

def test_engine_basic(sample_data):
    cand = StrategyCandidate(
        id="test",
        source_grammar="v1",
        entry_block={"type": EntryType.EMA_CROSS, "params": {"fast": 5, "slow": 10}},
        filter_blocks=[],
        exit_blocks=[{"type": ExitType.STOP_LOSS_ATR, "params": {"period": 14, "mult": 2.0}}]
    )

    engine = BacktestEngine(sample_data)
    res = engine.run(cand)

    assert "total_return" in res
    assert "equity_curve" in res
    assert len(res["equity_curve"]) >= 1

def test_engine_session_close(sample_data):
    # Ensure session close exit works
    cand = StrategyCandidate(
        id="test_sess",
        source_grammar="v1",
        entry_block={"type": EntryType.EMA_CROSS, "params": {"fast": 2, "slow": 5}},
        filter_blocks=[],
        exit_blocks=[
            {"type": ExitType.SESSION_CLOSE, "params": {"time": "15:25"}}
        ]
    )

    # Force a setup
    sample_data["close"] = np.random.normal(100, 2, 100)
    # Make EMA cross happen

    engine = BacktestEngine(sample_data)
    res = engine.run(cand)

    # We just check it runs without error and returns structure
    assert res["candidate_id"] == "test_sess"
