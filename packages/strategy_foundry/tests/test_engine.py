import pytest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyCandidate

def test_engine_run():
    # Create dummy data
    dates = pd.date_range("2023-01-01", periods=100)
    df = pd.DataFrame({
        "open": np.random.rand(100) * 10 + 100,
        "high": np.random.rand(100) * 10 + 105,
        "low": np.random.rand(100) * 10 + 95,
        "close": np.random.rand(100) * 10 + 100,
        "volume": np.random.randint(1000, 10000, 100)
    }, index=dates)

    # Simple strategy
    strategy = StrategyCandidate(
        id="test",
        source_code={
            "logic": [{"type": "ema_crossover", "params": {"fast": 5, "slow": 10}}],
            "risk": {"stop_loss_atr": 1.0, "take_profit_atr": 2.0}
        },
        created_at=0
    )

    engine = BacktestEngine()
    trades, equity, signals = engine.run(df, strategy)

    # Even if logic is random, it should return consistent types
    assert isinstance(trades, pd.DataFrame)
    assert isinstance(equity, pd.Series)
    assert isinstance(signals, pd.Series)

    if not trades.empty:
        assert "pnl" in trades.columns
        assert "entry_date" in trades.columns
