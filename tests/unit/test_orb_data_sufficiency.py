import pytest
from datetime import datetime, time, timedelta
from packages.core.strategies.orb import ORBStrategy
from packages.core.models import Bar, Instrument
from packages.core.strategies.base import StrategyContext

class MockInstrument:
    def __init__(self, token, symbol):
        self.token = token
        self.symbol = symbol
        self.tradingsymbol = symbol

def test_orb_partial_data_safety_check():
    """
    Verifies that ORBStrategy REJECTS calculating Opening Range if provided bars
    do not cover the start of the window (09:15).
    """
    # 1. Setup
    strategy = ORBStrategy("ORB_TEST", {"window_min": 15, "instruments": ["NIFTY"]})
    token = 123
    instrument = MockInstrument(token, "NIFTY")

    # 2. Create bars for the last ~8.3 minutes (100 bars) ending at 09:30
    # Window is 09:15 to 09:30.
    # Missing data: 09:15 to 09:21:40.

    base_date = datetime(2023, 1, 1)
    market_open = datetime.combine(base_date.date(), time(9, 15))
    current_time = datetime.combine(base_date.date(), time(9, 30))

    bars = []
    # Generate 100 bars ending at 9:30 (5 seconds each)
    # Start time = 09:21:40
    start_time = current_time - timedelta(seconds=100*5)

    for i in range(100):
        t = start_time + timedelta(seconds=i*5)
        # Price is flat 100
        bars.append(Bar(
            token=token,
            timestamp=t,
            open=100, high=100, low=100, close=100,
            volume=100, oi=0
        ))

    # 3. Update opening range
    strategy._update_opening_range(token, bars, current_time)

    # 4. Assert
    # The strategy should NOT have set the range because data is missing from 09:15
    assert token not in strategy.opening_ranges

    print("\n[Confirmed] ORBStrategy correctly rejected insufficient data starting at", bars[0].timestamp.time())

def test_orb_full_data_success():
    """
    Verifies that ORBStrategy accepts data if it covers the full window.
    """
    # 1. Setup
    strategy = ORBStrategy("ORB_TEST", {"window_min": 15, "instruments": ["NIFTY"]})
    token = 123

    base_date = datetime(2023, 1, 1)
    market_open = datetime.combine(base_date.date(), time(9, 15))
    current_time = datetime.combine(base_date.date(), time(9, 30))

    bars = []
    # Generate 180 bars (15 mins * 12 bars/min)
    # Start time = 09:15:00
    start_time = market_open

    for i in range(180):
        t = start_time + timedelta(seconds=i*5)
        bars.append(Bar(
            token=token,
            timestamp=t,
            open=100, high=100, low=100, close=100,
            volume=100, oi=0
        ))

    # 3. Update opening range
    strategy._update_opening_range(token, bars, current_time)

    # 4. Assert
    assert token in strategy.opening_ranges
    print("\n[Confirmed] ORBStrategy accepted full data starting at", bars[0].timestamp.time())
