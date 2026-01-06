import pandas as pd
import numpy as np
from packages.strategy_foundry.adapters.core_indicators import compute_all_indicators

def test_indicators_vectorized():
    # Create synthetic data
    dates = pd.date_range(start="2023-01-01", periods=100)
    df = pd.DataFrame({
        "open": np.random.rand(100) * 100,
        "high": np.random.rand(100) * 110,
        "low": np.random.rand(100) * 90,
        "close": np.random.rand(100) * 100,
        "volume": np.random.randint(1000, 10000, 100)
    }, index=dates)

    # Ensure high >= low
    df["high"] = np.maximum(df["high"], df["close"])
    df["low"] = np.minimum(df["low"], df["close"])

    res = compute_all_indicators(df)

    assert "rsi_14" in res.columns
    assert "atr_14" in res.columns
    assert "ema_50" in res.columns
    assert "supertrend" in res.columns

    # Check values not all NaN (after warmup)
    assert not pd.isna(res["rsi_14"].iloc[-1])
    assert not pd.isna(res["supertrend"].iloc[-1])
