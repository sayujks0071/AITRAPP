import pytest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import Strategy

# Mock Strategy
class MockStrat:
    def generate_positions(self, df):
        # Long from day 1 to day 3
        # indices: 0, 1, 2, 3...
        # s[1]=1, s[2]=1.
        s = pd.Series(0, index=df.index)
        s.iloc[1:3] = 1
        print("\nS values:", s.values)
        return s

    def apply_risk_overlay(self, df, s):
        return s

def test_engine_simple_trade():
    dates = pd.date_range("2023-01-01", periods=10)

    opens = [100.0] * 10
    opens[4] = 110.0 # Exit at 110

    df = pd.DataFrame({
        "open": opens,
        "high": [105]*10,
        "low": [95]*10,
        "close": [100]*10,
        "volume": [1000]*10
    }, index=dates)

    engine = BacktestEngine(initial_capital=10000)
    strat = MockStrat()
    eq, trades = engine.run(strat, df)

    print("Dates:", dates)
    print("Trades:", trades)

    assert not trades.empty
    trade = trades.iloc[0]

    assert trade["entry_price"] == 100.0
    assert trade["exit_price"] == 110.0
