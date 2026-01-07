
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

def benchmark_individual():
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

    iterations = 1000

    times = {}

    def measure(name, func):
        start = time.time()
        for _ in range(iterations):
            func()
        end = time.time()
        times[name] = (end - start) / iterations * 1000

    measure("TR", lambda: calc._calculate_tr(df))
    tr = calc._calculate_tr(df)

    measure("VWAP", lambda: calc._vwap(df))
    measure("ATR", lambda: calc._atr(df, tr=tr))
    measure("RSI", lambda: calc._rsi(df))
    measure("ADX", lambda: calc._adx(df, tr=tr))
    measure("EMA Fast", lambda: calc._ema(df["close"], calc.ema_fast))
    measure("EMA Slow", lambda: calc._ema(df["close"], calc.ema_slow))
    measure("Supertrend", lambda: calc._supertrend(df, tr=tr))
    measure("Bollinger", lambda: calc._bollinger_bands(df["close"]))
    measure("Donchian", lambda: calc._donchian(df))
    measure("OBV", lambda: calc._obv(df))
    measure("Hist Vol", lambda: calc._historical_volatility(df["close"]))

    print("Time per call (ms):")
    for name, t in sorted(times.items(), key=lambda x: x[1], reverse=True):
        print(f"{name}: {t:.4f} ms")

if __name__ == "__main__":
    benchmark_individual()
