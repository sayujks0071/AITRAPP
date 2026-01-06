import pandas as pd
import pytest
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.backtest.engine import BacktestEngine, Trade
from packages.strategy_foundry.adapters.core_costs import CostModel

@pytest.fixture
def sample_data():
    dates = pd.date_range("2024-01-01 09:15", "2024-01-05 15:30", freq="5min", tz="Asia/Kolkata")
    # Filter market hours
    dates = [d for d in dates if d.time() >= pd.Timestamp("09:15").time() and d.time() <= pd.Timestamp("15:30").time()]
    df = pd.DataFrame(index=dates)
    df["open"] = 100.0
    df["high"] = 101.0
    df["low"] = 99.0
    df["close"] = 100.5
    df["volume"] = 1000

    # Add trend
    df["close"] = df["close"] + (pd.Series(range(len(df))) * 0.1)
    df["high"] = df["close"] + 0.5
    df["low"] = df["close"] - 0.5
    return df

def test_engine_basic_run(sample_data):
    engine = BacktestEngine(CostModel())
    candidate = StrategyCandidate(
        id="test",
        entry_logic={"type": "EMA_CROSS"},
        exit_logic={"type": "TIME_STOP"},
        filters=[],
        timeframe="5m",
        params={"ema_fast": 5, "ema_slow": 10, "max_bars": 5}
    )

    equity, trades = engine.run_safe(candidate, sample_data)

    assert isinstance(equity, pd.DataFrame)
    assert "equity" in equity.columns
    # With pure linear trend, EMA cross might trigger.
    # Just ensure it runs without error.
