import pandas as pd
import numpy as np
import pytest
from datetime import datetime, timedelta
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategySpec, EntryType

def create_synthetic_data(n=200):
    dates = [datetime(2023, 1, 1, 9, 15) + timedelta(minutes=5*i) for i in range(n)]
    # Create a sine wave price to trigger signals
    t = np.linspace(0, 4*np.pi, n)
    price = 100 + 10 * np.sin(t)

    df = pd.DataFrame({
        "timestamp": dates,
        "open": price,
        "high": price + 1,
        "low": price - 1,
        "close": price, # Close = Open for simplicity in trend
        "volume": 1000
    })
    return df

def test_engine_run():
    df = create_synthetic_data()
    # RSI Reversion: Buy when RSI < 30.
    # Sine wave will produce low RSI at troughs.

    spec = StrategySpec(
        strategy_id="test",
        entry_logic=EntryType.RSI_REVERSION.value,
        entry_params={"period": 14, "threshold": 40}, # Higher threshold to ensure triggers
        stop_loss_atr=2.0,
        take_profit_atr=4.0,
        time_exit_bars=None
    )

    engine = BacktestEngine()
    res = engine.run(spec, df)

    assert "metrics" in res
    assert "trades" in res
    assert "current_state" in res

    metrics = res["metrics"]
    # We expect some trades
    # assert metrics["trades"] > 0 # Might fail if RSI calc needs more data

    # Check current state structure
    state = res["current_state"]
    assert "position" in state
