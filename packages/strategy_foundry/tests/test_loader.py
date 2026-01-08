
import pytest
import pandas as pd
import numpy as np
from packages.strategy_foundry.adapters import core_indicators as ind

def test_indicators_vectorized():
    # Create sample data
    df = pd.DataFrame({
        "close": np.arange(100, 200),
        "high": np.arange(101, 201),
        "low": np.arange(99, 199),
        "open": np.arange(100, 200)
    })

    # EMA
    e = ind.ema(df["close"], 10)
    assert not e.isnull().all()
    assert len(e) == 100

    # RSI
    r = ind.rsi(df["close"], 14)
    assert not r.isnull().all()

    # Supertrend
    s, d = ind.supertrend(df, 10, 3)
    assert not s.isnull().all()
    assert not d.isnull().all()
