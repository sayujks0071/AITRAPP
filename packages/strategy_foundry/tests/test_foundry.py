"""
Tests for Strategy Foundry.
"""
import pytest
import pandas as pd
import numpy as np
from packages.strategy_foundry.adapters.core_indicators import VectorizedIndicators
from packages.strategy_foundry.factory.grammar import Grammar
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.generator import StrategyGenerator

def test_indicators():
    df = pd.DataFrame({
        "high": np.random.rand(100) * 10 + 100,
        "low": np.random.rand(100) * 10 + 90,
        "close": np.random.rand(100) * 10 + 95,
        "volume": np.random.rand(100) * 1000
    })

    atr = VectorizedIndicators.atr(df, 14)
    assert len(atr) == 100
    assert not atr.isnull().all()

def test_grammar():
    strat = Grammar.generate_random("5m")
    assert strat.timeframe == "5m"
    assert "entry" in strat.to_json()

def test_engine():
    # Mock Data
    dates = pd.date_range("2023-01-01", periods=100, freq="5min", tz="Asia/Kolkata")
    df = pd.DataFrame({
        "open": 100.0,
        "high": 105.0,
        "low": 95.0,
        "close": 101.0,
        "volume": 1000
    }, index=dates)

    # Create a trend that triggers EMA cross
    # Fast EMA (10) > Slow EMA (20)
    # Make close rise
    df["close"] = np.linspace(100, 200, 100)

    gen = StrategyGenerator()
    candidates = gen.generate_candidates(5, "5m")

    engine = BacktestEngine()

    # Try to find a valid trade
    for cand in candidates:
        res = engine.run(cand, df)
        if res["total_trades"] > 0:
            assert res["final_equity"] != 100000.0
            break

if __name__ == "__main__":
    test_indicators()
    test_grammar()
    test_engine()
    print("Tests Passed")
