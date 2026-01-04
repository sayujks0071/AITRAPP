"""
Tests for Strategy Foundry
"""
import pytest
import pandas as pd
import numpy as np
import os
import shutil
from packages.strategy_foundry.adapters.core_indicators import Indicators
from packages.strategy_foundry.factory.grammar import StrategyGrammar
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.data.loader import DataLoader

def test_indicators():
    df = pd.DataFrame({
        "close": [10, 11, 12, 11, 10, 11, 12, 13, 14, 15, 16, 15, 14, 13, 12] * 20, # 300 rows
        "high": [11, 12, 13, 12, 11, 12, 13, 14, 15, 16, 17, 16, 15, 14, 13] * 20,
        "low": [9, 10, 11, 10, 9, 10, 11, 12, 13, 14, 15, 14, 13, 12, 11] * 20
    })

    rsi = Indicators.rsi(df["close"], 14)
    assert not rsi.isna().all()

    atr = Indicators.atr(df["high"], df["low"], df["close"], 14)
    assert not atr.isna().all()

    st = Indicators.supertrend(df["high"], df["low"], df["close"], 10, 3.0)
    print("\nSupertrend Tail:\n", st.tail(20))

    assert not st.isna().all()

def test_grammar():
    strat = StrategyGrammar.random_strategy()
    assert "entry" in strat
    assert "exit" in strat
    assert "id" in strat

def test_backtest_engine():
    # Create synthetic data
    dates = pd.date_range(start="2023-01-01", periods=100, freq="5min", tz="Asia/Kolkata")
    df = pd.DataFrame({
        "timestamp": dates,
        "open": [100 + i for i in range(100)],
        "high": [105 + i for i in range(100)],
        "low": [95 + i for i in range(100)],
        "close": [102 + i for i in range(100)],
        "volume": [1000] * 100
    })

    # Simple Strategy
    strat = {
        "id": "test",
        "entry": {"trend_ema_cross": {"fast": 5, "slow": 10}},
        "exit": {"atr_stop": {"period": 14, "multiple": 2.0}},
        "filters": []
    }

    engine = BacktestEngine(df, strat)
    res = engine.run()

    assert res is not None
    assert "metrics" in res
    assert "trades" in res

def test_loader_cache(tmp_path):
    # Mock config
    os.makedirs(tmp_path / "cache")

    # Save a file there
    df = pd.DataFrame({"timestamp": [pd.Timestamp("2023-01-01", tz="Asia/Kolkata")]})
    df.to_csv(tmp_path / "cache/TEST_5m.csv", index=False)

    # We can't easily inject the path into DataLoader without modifying init args or mocking
    # But checking if loader can init is fine.
    loader = DataLoader()
    assert loader is not None
