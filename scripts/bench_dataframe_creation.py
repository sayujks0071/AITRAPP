
import time
import pandas as pd
import numpy as np

# Mock Bar class
class Bar:
    def __init__(self, o, h, l, c, v):
        self.open = o
        self.high = h
        self.low = l
        self.close = c
        self.volume = v

def benchmark_dataframe_creation():
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

    iterations = 10000

    # 1. List of Dicts (Current)
    start = time.time()
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
    end = time.time()
    duration_current = end - start
    print(f"List of Dicts: {duration_current:.4f}s ({duration_current/iterations*1000:.4f}ms/call)")

    # 2. Dict of Lists (Proposed)
    start = time.time()
    for _ in range(iterations):
        data = {
            "open": [b.open for b in bars],
            "high": [b.high for b in bars],
            "low": [b.low for b in bars],
            "close": [b.close for b in bars],
            "volume": [b.volume for b in bars]
        }
        df = pd.DataFrame(data)
    end = time.time()
    duration_proposed = end - start
    print(f"Dict of Lists: {duration_proposed:.4f}s ({duration_proposed/iterations*1000:.4f}ms/call)")

    # 3. Pre-allocated arrays (Manual)
    # If bars is a deque, we can iterate once
    start = time.time()
    for _ in range(iterations):
        n = len(bars)
        opens = [0.0] * n
        highs = [0.0] * n
        lows = [0.0] * n
        closes = [0.0] * n
        volumes = [0] * n

        for i, b in enumerate(bars):
            opens[i] = b.open
            highs[i] = b.high
            lows[i] = b.low
            closes[i] = b.close
            volumes[i] = b.volume

        df = pd.DataFrame({
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes
        })
    end = time.time()
    duration_manual = end - start
    print(f"Single Loop: {duration_manual:.4f}s ({duration_manual/iterations*1000:.4f}ms/call)")

if __name__ == "__main__":
    benchmark_dataframe_creation()
