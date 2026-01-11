import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from packages.strategy_foundry.factory.grammar import StrategyConfig, StrategyRule
from packages.strategy_foundry.backtest.engine import BacktestEngine

def test_engine_run():
    # Mock Data
    dates = pd.date_range(start="2024-01-01", periods=1000, freq="5min", tz="Asia/Kolkata")
    df = pd.DataFrame({
        "open": 100 + np.random.randn(1000).cumsum(),
        "high": 0,
        "low": 0,
        "close": 0,
        "volume": 1000
    }, index=dates)
    df["high"] = df["open"] + 1
    df["low"] = df["open"] - 1
    df["close"] = df["open"] + 0.5

    # Simple Strategy: EMA Cross
    strat = StrategyConfig(
        entry_rules=[StrategyRule("TREND_EMA_CROSS", {"fast": 10, "slow": 20})],
        exit_rules=[StrategyRule("STOP_ATR", {"multiplier": 2.0})],
        filters=[]
    )

    engine = BacktestEngine()
    res = engine.run(df, strat)

    assert "metrics" in res
    assert "trades" in res
    assert isinstance(res["metrics"]["sharpe"], float)
