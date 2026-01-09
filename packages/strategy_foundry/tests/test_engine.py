"""
Tests for Backtest Engine
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyConfig
from packages.strategy_foundry.adapters.core_market_hours import IST

@pytest.fixture
def sample_data():
    # Generate synthetic intraday data (Asia/Kolkata)
    dates = pd.date_range(start="2023-01-01 09:15", end="2023-01-05 15:30", freq="5min", tz=IST)
    dates = dates[dates.indexer_between_time("09:15", "15:30")]

    n = len(dates)
    # create a strong trend
    price = np.linspace(100, 200, n)
    # Add some noise
    noise = np.random.normal(0, 0.5, n)
    price = price + noise

    df = pd.DataFrame({
        "open": price,
        "high": price + 2,
        "low": price - 2,
        "close": price + 1,
        "volume": [1000] * n
    }, index=dates)
    return df

def test_engine_execution_simple(sample_data):
    # EMA Cross should definitely trigger on a 100->200 trend
    config = StrategyConfig(
        entry_block="entry_trend_ema_cross",
        entry_params={"fast_period": 5, "slow_period": 20, "adx_filter": False},
        risk_block="risk_atr",
        risk_params={"atr_period": 14, "multiplier": 2.0, "trailing": False},
        exit_block="exit_time",
        exit_params={"max_bars": 10}
    )

    engine = BacktestEngine(sample_data)
    trades, equity = engine.run(config)

    assert not trades.empty
    assert "pnl" in trades.columns
    assert len(equity) == len(sample_data)

def test_engine_eod_exit(sample_data):
    # Use EMA cross to ensure entry
    config = StrategyConfig(
        entry_block="entry_trend_ema_cross",
        entry_params={"fast_period": 5, "slow_period": 20, "adx_filter": False},
        risk_block="risk_atr",
        risk_params={"atr_period": 14, "multiplier": 10.0, "trailing": False}, # Wide stop
        exit_block="exit_time",
        exit_params={"max_bars": 1000} # Very long hold
    )

    engine = BacktestEngine(sample_data)
    trades, _ = engine.run(config)

    assert not trades.empty

    # Check if any trades exited with reason "EOD"
    eod_exits = trades[trades['reason'] == "EOD"]

    # It's possible that on last day we are still holding.
    # The trend is up.
    # We should have EOD exits every day if we enter early.

    assert not eod_exits.empty

    # Verify exit time is near 15:25
    for ts in eod_exits['exit_time']:
        assert ts.hour >= 15

def test_engine_costs(sample_data):
    config = StrategyConfig(
        entry_block="entry_trend_ema_cross",
        entry_params={"fast_period": 5, "slow_period": 20, "adx_filter": False},
        risk_block="risk_atr",
        risk_params={"atr_period": 14, "multiplier": 2.0, "trailing": False},
        exit_block="exit_time",
        exit_params={"max_bars": 5}
    )

    eng1 = BacktestEngine(sample_data, spread_guard_bps=0.0)
    t1, _ = eng1.run(config)

    eng2 = BacktestEngine(sample_data, spread_guard_bps=50.0)
    t2, _ = eng2.run(config)

    assert len(t1) == len(t2)
    # PnL should be lower in t2
    if not t1.empty:
        assert t2['pnl'].sum() < t1['pnl'].sum()
