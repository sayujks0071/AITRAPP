import pytest
import pandas as pd
import numpy as np
from packages.strategy_foundry.factory.grammar import EmaCrossEntry

def test_ema_cross_params_matter():
    dates = pd.date_range("2023-01-01", periods=100)
    # Sine wave to have crossings
    t = np.linspace(0, 4*np.pi, 100)
    prices = 100 + 10*np.sin(t)

    df = pd.DataFrame({
        "open": prices,
        "high": prices+1,
        "low": prices-1,
        "close": prices,
        "volume": 1000
    }, index=dates)

    # Fast Cross
    rule1 = EmaCrossEntry("Fast", {"fast": 5, "slow": 10})
    sig1 = rule1.compute(df, {})

    # Slow Cross
    rule2 = EmaCrossEntry("Slow", {"fast": 20, "slow": 50})
    sig2 = rule2.compute(df, {})

    # They should differ
    assert not sig1.equals(sig2)

    print("Signal 1 sum:", sig1.abs().sum())
    print("Signal 2 sum:", sig2.abs().sum())

    assert sig1.abs().sum() > 0
    assert sig2.abs().sum() > 0 # Should have some signals
