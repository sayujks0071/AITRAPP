import time
import numpy as np
import pandas as pd
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import Strategy

def generate_data(n=30000):
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=n, freq="5min", tz="Asia/Kolkata")

    # Random walk
    closes = 10000 + np.random.randn(n).cumsum()
    opens = closes + np.random.randn(n) * 5
    highs = np.maximum(opens, closes) + np.abs(np.random.randn(n) * 5)
    lows = np.minimum(opens, closes) - np.abs(np.random.randn(n) * 5)
    volume = np.abs(np.random.randn(n) * 1000) + 100

    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volume
    }, index=dates)
    return df

def run_benchmark():
    df = generate_data(n=50000) # Approx 6 months of 5m data
    engine = BacktestEngine()

    # Simple EMA Crossover Strategy
    strategy = Strategy(
        entry_blocks=[{
            "type": "ema_crossover",
            "params": {"fast": 10, "slow": 30}
        }],
        exit_blocks=[],
        filters=[]
    )

    print(f"Running benchmark on {len(df)} bars...")

    # Warmup
    engine.run(strategy, df)

    start_time = time.time()
    iterations = 5
    for _ in range(iterations):
        engine.run(strategy, df)

    end_time = time.time()
    avg_time = (end_time - start_time) / iterations

    print(f"Average Time: {avg_time:.4f}s")

if __name__ == "__main__":
    run_benchmark()
