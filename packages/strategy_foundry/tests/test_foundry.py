import pytest
import pandas as pd
import numpy as np
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.backtest.engine import FastBacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyCandidate, StrategyGrammar
from packages.strategy_foundry.factory.generator import GeneratedStrategy

def test_loader_synthetic():
    loader = DataLoader()
    df = loader.load_data("TEST_SYM", force_refresh=True) # Will trigger synthetic
    assert not df.empty
    assert "close" in df.columns
    assert isinstance(df.index, pd.DatetimeIndex)

def test_grammar_generation():
    cand = StrategyGrammar.generate_random()
    assert isinstance(cand, StrategyCandidate)
    assert "entry_type" in cand.grammar
    assert cand.id is not None

def test_engine_run():
    # Setup dummy data
    dates = pd.date_range("2020-01-01", periods=100)
    df = pd.DataFrame({
        "open": 100, "high": 105, "low": 95, "close": 102, "volume": 1000
    }, index=dates)
    # Add trend
    df["close"] = np.linspace(100, 200, 100)
    df["high"] = df["close"] + 5
    df["low"] = df["close"] - 5

    cand = StrategyGrammar.generate_random()
    strategy = GeneratedStrategy(cand)

    engine = FastBacktestEngine(df)
    res = engine.run(strategy)

    assert "metrics" in res
    assert "equity_curve" in res
    assert "sharpe" in res["metrics"]
