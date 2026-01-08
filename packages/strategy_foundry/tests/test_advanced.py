"""
Tests for WFA and Promotion.
"""
import pytest
import pandas as pd
import numpy as np
import os
import shutil
from packages.strategy_foundry.backtest.walkforward import WalkForwardValidator
from packages.strategy_foundry.selection.promote import Promoter
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.factory.grammar import Grammar

def test_wfa_validator():
    # Mock Data (Trend)
    dates = pd.date_range("2023-01-01", periods=1000, freq="5min", tz="Asia/Kolkata")
    df = pd.DataFrame({
        "open": np.linspace(100, 200, 1000),
        "high": np.linspace(101, 201, 1000),
        "low": np.linspace(99, 199, 1000),
        "close": np.linspace(100.5, 200.5, 1000),
        "volume": 1000
    }, index=dates)

    # Random strategy
    strat = Grammar.generate_random("5m")

    engine = BacktestEngine()
    ranker = Ranker()
    validator = WalkForwardValidator(engine, ranker, folds=2, is_fast_mode=True)

    res = validator.validate(strat, df)

    assert res["valid"] is True
    assert "metrics" in res
    assert "fold_metrics" in res
    assert len(res["fold_metrics"]) == 2

def test_promoter():
    promoter = Promoter()

    incumbent = {
        "score": 100,
        "metrics": {"max_dd": 0.20, "sharpe": 1.0}
    }

    # Case 1: Worse score, no risk reduction -> False
    challenger_bad = {
        "score": 90,
        "metrics": {"max_dd": 0.20, "sharpe": 0.9}
    }
    assert promoter.should_promote(challenger_bad, incumbent) is False

    # Case 2: Better score (>10%) -> True
    challenger_good = {
        "score": 115,
        "metrics": {"max_dd": 0.20, "sharpe": 1.2}
    }
    assert promoter.should_promote(challenger_good, incumbent) is True

    # Case 3: Risk reduction (DD -5%), Sharpe stable -> True
    challenger_risk = {
        "score": 95,
        "metrics": {"max_dd": 0.14, "sharpe": 0.95} # DD reduced by 6%, Sharpe change -0.05
    }
    assert promoter.should_promote(challenger_risk, incumbent) is True

if __name__ == "__main__":
    test_wfa_validator()
    test_promoter()
    print("Tests Passed")
