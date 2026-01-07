
import time
import pandas as pd
import numpy as np
from packages.core.indicators import IndicatorCalculator

# Mock Bar class
class Bar:
    def __init__(self, o, h, l, c, v):
        self.open = o
        self.high = h
        self.low = l
        self.close = c
        self.volume = v

def benchmark_breakdown():
    calc = IndicatorCalculator()

    # Create 200 bars
    bars = [
        Bar(
            100.0 + i * 0.1,
            101.0 + i * 0.1,
            99.0 + i * 0.1,
            100.5 + i * 0.1,
            1000 + i
        )
        for i in range(200)
    ]

    iterations = 1000

    # 1. Measure DataFrame Creation
    start_df = time.time()
    for _ in range(iterations):
        df = pd.DataFrame([
            {
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume
            }
            for b in bars
        ])
    end_df = time.time()
    time_df = end_df - start_df

    # Pre-create DataFrame for next step
    df = pd.DataFrame([
        {
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume
        }
        for b in bars
    ])

    # 2. Measure Calculation
    start_calc = time.time()
    for _ in range(iterations):
        indicators = calc.compute_all(df)
    end_calc = time.time()
    time_calc = end_calc - start_calc

    print(f"DataFrame Creation: {time_df:.4f}s ({time_df/iterations*1000:.4f}ms/call)")
    print(f"Calculation: {time_calc:.4f}s ({time_calc/iterations*1000:.4f}ms/call)")
    print(f"Total: {time_df + time_calc:.4f}s")

if __name__ == "__main__":
    benchmark_breakdown()
