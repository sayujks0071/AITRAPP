import pandas as pd
import numpy as np
import pytest
from datetime import datetime, timedelta
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategySpec, StrategyBlock

def create_synthetic_data():
    dates = pd.date_range(start="2023-01-01 09:15", periods=500, freq="5min")
    # Create a trend
    price = 10000.0
    data = []
    for d in dates:
        price += np.random.normal(0, 5)
        # Add a big jump for breakout
        if d.hour == 10 and d.minute == 0:
            price += 50

        data.append({
            "Open": price,
            "High": price + 5,
            "Low": price - 5,
            "Close": price + 2,
            "Volume": 1000
        })
    df = pd.DataFrame(data, index=dates)
    return df

def test_engine_run():
    data = create_synthetic_data()

    # Strategy: Donchian Breakout (Period 10) + ATR Stop (Period 14, Mult 2.0)
    blocks = [
        StrategyBlock(type="donchian_breakout", params={"period": 10}),
        StrategyBlock(type="atr_stop", params={"period": 14, "multiplier": 2.0})
    ]
    spec = StrategySpec(blocks=blocks, timeframe="5m", instrument="TEST")

    engine = BacktestEngine(data)
    result = engine.run(spec)

    metrics = result["metrics"]
    trades = result["trades"]

    # We expect some trades due to synthetic volatility
    # It's okay if 0, but we want to ensure no crash
    assert "total_trades" in metrics
    assert "sharpe_ratio" in metrics

    # Check trade structure
    if trades:
        t = trades[0]
        assert "entry_time" in t
        assert "pnl" in t
        assert "reason" in t

def test_engine_indicators_precalc():
    data = create_synthetic_data()
    blocks = [
        StrategyBlock(type="ema_cross", params={"fast": 5, "slow": 10}),
    ]
    spec = StrategySpec(blocks=blocks, timeframe="5m", instrument="TEST")

    engine = BacktestEngine(data)
    indicators = engine._compute_indicators(spec)

    assert "ema_5" in indicators
    assert "ema_10" in indicators
    assert len(indicators["ema_5"]) == len(data)
