
import numpy as np
import pandas as pd
from packages.strategy_foundry.adapters.core_indicators import VectorizedIndicatorCalculator


def test_rsi():
    close = np.linspace(100, 110, 200)
    calc = VectorizedIndicatorCalculator()
    rsi = calc.rsi(close, 14)
    assert len(rsi) == 200
    assert (~np.isnan(rsi)).sum() > 0


def test_atr():
    calc = VectorizedIndicatorCalculator()
    high = np.linspace(105, 205, 150)
    low = high - 5
    close = (high + low) / 2
    atr = calc.atr(high, low, close, 14)
    assert len(atr) == 150
    assert np.isnan(atr[:13]).all()


def test_ema():
    calc = VectorizedIndicatorCalculator()
    series = pd.Series(np.arange(50, dtype=float))
    ema = calc.ema(series, 5)
    assert len(ema) == 50
    assert float(ema.iloc[-1]) > float(ema.iloc[0])
