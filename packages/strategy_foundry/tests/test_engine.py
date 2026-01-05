
import pytest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import BacktestEngine

@pytest.fixture
def sample_data():
    dates = pd.date_range("2023-01-01", periods=100)
    df = pd.DataFrame({
        "open": np.linspace(100, 200, 100),
        "high": np.linspace(105, 205, 100),
        "low": np.linspace(95, 195, 100),
        "close": np.linspace(102, 202, 100),
        "volume": 1000
    }, index=dates)
    return df

def test_engine_runs(sample_data):
    engine = BacktestEngine(sample_data)

    config = {
        "blocks": [
            {"type": "ENTRY", "subtype": "EMA_CROSS", "params": {"fast": 5, "slow": 10}},
            {"type": "EXIT", "subtype": "ATR_STOP", "params": {"multiplier": 2.0}}
        ]
    }

    res = engine.run(config)
    assert "trades" in res
    assert "equity_curve" in res
    assert "final_equity" in res
