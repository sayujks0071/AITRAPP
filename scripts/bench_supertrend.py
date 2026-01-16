
import time
import numpy as np
import pandas as pd
import sys
import os

# Add repo root to path
sys.path.append(os.getcwd())

from packages.strategy_foundry.adapters.core_indicators import VectorIndicatorCalculator

def bench_supertrend():
    # Setup data
    N = 10000
    df = pd.DataFrame({
        'high': np.random.rand(N) * 100 + 100,
        'low': np.random.rand(N) * 100,
        'close': np.random.rand(N) * 100 + 50,
        'open': np.random.rand(N) * 100 + 50,
    })

    calc = VectorIndicatorCalculator()

    # Warmup with fallback params
    calc.supertrend(df, 11, 3.0)

    iterations = 100
    start_time = time.time()

    for _ in range(iterations):
        # Use non-default period to ensure fallback is used
        calc.supertrend(df, 11, 3.0)

    end_time = time.time()
    avg_time = (end_time - start_time) / iterations

    print(f"Average time per call: {avg_time*1000:.4f} ms")
    print(f"Total time for {iterations} iterations: {end_time - start_time:.4f} s")

if __name__ == "__main__":
    bench_supertrend()
