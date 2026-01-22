import time
import pandas as pd
import numpy as np
import sys
import os

# Ensure packages can be imported
sys.path.append(os.getcwd())

from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import Strategy

class MockStrategy:
    def __init__(self):
        pass

    def calculate_signals(self, data):
        n = len(data)
        np.random.seed(42) # Deterministic
        # Random entries: 1% chance of entry
        entries = np.zeros(n)
        mask = np.random.random(n) < 0.01
        entries[mask] = 1

        # Random exits: 2% chance
        exits = np.random.random(n) < 0.02

        return pd.Series(entries, index=data.index), pd.Series(exits, index=data.index)

    def get_risk_params(self):
        return {"trailing_stop_pct": 0.01}

def generate_data(days=30):
    np.random.seed(42) # Deterministic
    dates = []
    # Start on Monday
    start_date = pd.Timestamp("2024-01-01")

    for i in range(days):
        d = start_date + pd.Timedelta(days=i)
        # Skip weekends for realistic data, though logic handles it
        if d.weekday() >= 5: continue

        # 09:15 to 15:25
        ts = pd.date_range(start=d + pd.Timedelta(hours=9, minutes=15),
                           end=d + pd.Timedelta(hours=15, minutes=25),
                           freq="5min")
        dates.extend(ts)

    n = len(dates)
    print(f"Generating {n} bars...")

    df = pd.DataFrame({
        "open": np.random.uniform(100, 200, n),
        "high": np.random.uniform(100, 200, n),
        "low": np.random.uniform(100, 200, n),
        "close": np.random.uniform(100, 200, n),
        "volume": np.random.uniform(1000, 10000, n)
    }, index=pd.DatetimeIndex(dates))

    # Fix High/Low
    df["high"] = df[["open", "close", "high"]].max(axis=1)
    df["low"] = df[["open", "close", "low"]].min(axis=1)

    return df

def run_benchmark():
    # 250 days ~ 1 year of data
    df = generate_data(days=250)
    strategy = MockStrategy()
    engine = BacktestEngine()

    print("Starting Backtest...")
    start_time = time.time()
    engine.run(strategy, df)
    end_time = time.time()

    print(f"Backtest took: {end_time - start_time:.4f} seconds")

if __name__ == "__main__":
    run_benchmark()
