import time
import numpy as np
import pandas as pd
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyType, FilterType, ExitType

def generate_data(n=30000):
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=n, freq="5min")

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
    df = generate_data()
    engine = BacktestEngine()

    spec = {
        "id": "bench_strat",
        "direction": "LONG",
        "strategy_type": StrategyType.SUPERTREND_FOLLOW.value,
        "strategy_params": {"period": 10, "multiplier": 3.0},
        "filter_type": FilterType.NO_FILTER.value,
        "filter_params": {},
        "exit_type": ExitType.FIXED_RR.value,
        "exit_params": {"sl_mult": 2.0, "tp_mult": 3.0},
        "session_close_time": "15:25"
    }

    print(f"Running benchmark on {len(df)} bars...")

    # Warmup
    engine.run(df, spec)

    start_time = time.time()
    iterations = 5
    results = []

    for _ in range(iterations):
        res = engine.run(df, spec)
        results.append(res)

    end_time = time.time()
    avg_time = (end_time - start_time) / iterations

    # Checksum (sum of final equity)
    final_equity_sum = sum([r["equity_curve"].iloc[-1] for r in results])

    print(f"Average Time: {avg_time:.4f}s")
    print(f"Final Equity Checksum: {final_equity_sum:.2f}")

    # Verify equity curve structure
    eq = results[0]["equity_curve"]
    print(f"Equity Curve Length: {len(eq)}")
    print(f"Equity Curve Head: {eq.head().tolist()}")

if __name__ == "__main__":
    run_benchmark()
