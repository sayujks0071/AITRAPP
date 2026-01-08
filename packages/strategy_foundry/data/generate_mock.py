
import pandas as pd
import numpy as np
import os

dates = pd.date_range("2020-01-01", periods=1000)
df = pd.DataFrame({
    "date": dates,
    "open": np.random.uniform(100, 200, 1000),
    "high": np.random.uniform(200, 210, 1000),
    "low": np.random.uniform(90, 100, 1000),
    "close": np.random.uniform(100, 200, 1000),
    "volume": np.random.randint(1000, 10000, 1000)
})

# Make sure close is somewhat continuous
df["close"] = 100 + np.cumsum(np.random.randn(1000))
df["open"] = df["close"].shift(1).fillna(100)
df["high"] = df[["open", "close"]].max(axis=1) + np.random.rand(1000)
df["low"] = df[["open", "close"]].min(axis=1) - np.random.rand(1000)

os.makedirs("packages/strategy_foundry/data/cache", exist_ok=True)
df.to_csv("packages/strategy_foundry/data/cache/NIFTY.csv", index=False)
df.to_csv("packages/strategy_foundry/data/cache/SENSEX.csv", index=False)
print("Mock data generated")
