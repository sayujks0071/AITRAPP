import pytest
import pandas as pd
from packages.strategy_foundry.factory.grammar import Strategy, EmaCrossBlock

def test_strategy_generation():
    block = EmaCrossBlock(10, 20)
    strat = Strategy([block], 2.0, 4.0)
    assert strat.id is not None
    assert "EmaCross" in strat.rule_summary

def test_position_generation():
    # Mock DF
    df = pd.DataFrame({
        "close": [100, 105, 110, 115, 120, 115, 110, 105, 100],
        "high": [102, 107, 112, 117, 122, 117, 112, 107, 102],
        "low": [98, 103, 108, 113, 118, 113, 108, 103, 98],
        "open": [100]*9
    })

    # Need long enough for EMA
    df = pd.DataFrame({
        "close": range(100),
        "high": range(100),
        "low": range(100),
        "open": range(100)
    })

    block = EmaCrossBlock(5, 10) # Short periods
    strat = Strategy([block], 2.0, 4.0)

    pos = strat.generate_positions(df)
    assert len(pos) == len(df)
    assert set(pos.unique()).issubset({-1, 0, 1})
