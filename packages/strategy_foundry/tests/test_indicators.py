
import pytest
import pandas as pd
import numpy as np
from packages.strategy_foundry.adapters.core_indicators import VectorizedIndicators

def test_rsi():
    close = np.random.random(100) * 100
    rsi = VectorizedIndicators.rsi(close, 14)
    assert len(rsi) == 100
    assert not np.all(np.isnan(rsi))

def test_atr():
    h = np.random.random(100) * 100 + 10
    l = h - 5
    c = (h + l) / 2
    atr = VectorizedIndicators.atr(h, l, c, 14)
    assert len(atr) == 100

def test_ema():
    c = np.arange(100)
    ema = VectorizedIndicators.ema(c, 10)
    assert len(ema) == 100
    assert ema[-1] > ema[0]
