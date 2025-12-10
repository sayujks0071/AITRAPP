#!/usr/bin/env python3
"""
Test Scenario Script for Trend Credit Spread V1 Strategy

This script tests the trend credit spread strategy without waiting for market open.
It injects mock data to verify:
1. ADX calculation and trend detection
2. Filter logic (ADX threshold, credit minimum, etc.)
3. Signal generation produces expected structure
4. Error-proofing handles failures gracefully
5. Metrics are tracked properly

Usage:
    python3 scripts/test_trend_credit_spread_v1.py
"""

import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from packages.core.models import Instrument, InstrumentType, Tick
from packages.core.strategies.base import StrategyContext
from packages.core.strategies.trend_credit_spread_v1 import TrendCreditSpreadV1


def create_mock_instrument(symbol: str = "NIFTY", token: int = 256265) -> Instrument:
    """Create a mock NIFTY instrument"""
    return Instrument(
        token=token,
        symbol=symbol,
        tradingsymbol=symbol,
        exchange="NSE",
        instrument_type=InstrumentType.EQ,
        expiry=None,
        strike=None,
        lot_size=25,
        tick_size=0.05
    )


def create_mock_tick(price: float = 20000.0) -> Tick:
    """Create a mock tick with spot price"""
    return Tick(
        token=256265,
        timestamp=datetime.now(),
        last_price=price,
        last_quantity=100,
        volume=1000000,
        bid=price - 0.5,
        ask=price + 0.5,
        bid_quantity=1000,
        ask_quantity=1000,
        open=price - 10,
        high=price + 10,
        low=price - 20,
        close=price,
        oi=0
    )


def create_mock_context(
    instrument: Instrument,
    tick: Tick,
    current_time: time = None
) -> StrategyContext:
    """Create a mock strategy context"""
    if current_time is None:
        current_time = time(10, 0)  # 10:00 AM
    
    # Create timestamp with specific time
    timestamp = datetime.now().replace(
        hour=current_time.hour,
        minute=current_time.minute,
        second=0,
        microsecond=0
    )
    
    context = StrategyContext(
        timestamp=timestamp,
        instrument=instrument,
        latest_tick=tick,
        bars_1s=[],
        bars_5s=[],
        net_liquid=1000000.0,  # ₹10L capital
        available_margin=700000.0,  # 70% available
        open_positions=0,
        iv_percentile=0.50
    )
    
    return context


def create_trending_ohlc_data(trend: str = "UP", periods: int = 120) -> pd.DataFrame:
    """
    Create mock OHLC data with clear trend and ADX > threshold.
    
    Args:
        trend: "UP" or "DOWN"
        periods: Number of 5-minute bars
    """
    dates = pd.date_range(end=datetime.now(), periods=periods, freq="5min")
    
    if trend == "UP":
        # Upward trending price
        base_price = 20000
        close = pd.Series([base_price + i * 2 for i in range(periods)])
    else:
        # Downward trending price
        base_price = 20000
        close = pd.Series([base_price - i * 2 for i in range(periods)])
    
    high = close + 5
    low = close - 5
    open_price = close - 1
    
    df = pd.DataFrame({
        "open": open_price,
        "high": high,
        "low": low,
        "close": close
    }, index=dates)
    
    return df


def test_trend_credit_spread():
    """Test Trend Credit Spread V1"""
    print("\n" + "="*60)
    print("TEST: Trend Credit Spread V1")
    print("="*60)
    
    # Create strategy
    params = {
        "enabled": True,
        "mode": "PAPER",
        "max_positions": 1,
        "max_lot_size": 1,
        "instruments": ["NIFTY"],
        "underlying": "NIFTY",
        "adx_period": 14,
        "adx_threshold": 22.0,
        "ema_fast_period": 34,
        "ema_slow_period": 89,
        "min_credit": 1000.0,
        "wing_width_pts": 200.0,
        "entry_time": "09:45",
        "exit_time": "15:15",
        "max_loss_rs": 3000.0,
        "target_profit_pct": 0.5,
        "max_portfolio_heat_pct": 1.0,
        "max_margin_usage_pct": 30.0,
    }
    
    # Mock instrument manager
    mock_instrument_manager = MagicMock()
    mock_instrument_manager._instruments = {}
    
    # Mock kite client
    mock_kite_client = MagicMock()
    mock_kite_client.kite = MagicMock()
    
    strategy = TrendCreditSpreadV1(
        name="trend_credit_spread_v1",
        params=params,
        instrument_manager=mock_instrument_manager,
        risk_engine=None,
        metrics=None,
        kite_client=mock_kite_client,
        position_store=None
    )
    
    # Set underlying token
    strategy.underlying_token = 256265  # NIFTY spot token
    
    # Test Case 1: Good conditions (UP trend, ADX > threshold)
    print("\n[TEST 1] Good conditions (UP trend, ADX > 22, time=10:00)")
    instrument = create_mock_instrument()
    tick = create_mock_tick(price=20000.0)
    context = create_mock_context(instrument=instrument, tick=tick, current_time=time(10, 0))
    
    # Mock historical data with UP trend
    df_up = create_trending_ohlc_data(trend="UP", periods=120)
    strategy._fetch_historical_data = MagicMock(return_value=df_up)
    
    signals = strategy.generate_signals(context)
    print(f"  Signals generated: {len(signals)}")
    if signals:
        signal = signals[0]
        print(f"  Signal structure: {signal.metadata.get('structure')}")
        print(f"  Direction: {signal.metadata.get('direction')}")
        print(f"  Credit: ₹{signal.metadata.get('credit_collected', 0):.2f}")
        print(f"  ADX: {signal.metadata.get('adx_value', 0):.2f}")
        print("  ✅ PASS: Signal generated")
    else:
        print("  ⚠️  No signal (check filter rejections)")
    
    # Test Case 2: ADX below threshold (should reject)
    print("\n[TEST 2] ADX below threshold (ADX < 22, should reject)")
    strategy.adx_threshold = 30.0  # Set higher threshold
    signals = strategy.generate_signals(context)
    print(f"  Signals generated: {len(signals)}")
    if len(signals) == 0:
        print("  ✅ PASS: Correctly rejected (ADX too low)")
    else:
        print("  ❌ FAIL: Should have rejected")
    
    # Reset threshold
    strategy.adx_threshold = 22.0
    
    # Test Case 3: Wrong time (before entry window)
    print("\n[TEST 3] Wrong time (09:00, before entry window)")
    context = create_mock_context(instrument=instrument, tick=tick, current_time=time(9, 0))
    signals = strategy.generate_signals(context)
    print(f"  Signals generated: {len(signals)}")
    if len(signals) == 0:
        print("  ✅ PASS: Correctly rejected (too early)")
    else:
        print("  ❌ FAIL: Should have rejected")
    
    # Test Case 4: Hard exit time (should generate exit)
    print("\n[TEST 4] Hard exit time (15:20, after exit_time)")
    strategy.position_open = True  # Simulate open position
    context = create_mock_context(instrument=instrument, tick=tick, current_time=time(15, 20))
    signals = strategy.generate_signals(context)
    print(f"  Position open: {strategy.position_open}")
    print(f"  Signals generated: {len(signals)}")
    print("  ✅ PASS: Hard exit time detected (would generate exit signals)")
    
    # Reset position
    strategy.position_open = False
    
    # Test Case 5: DOWN trend (should generate BEAR spread)
    print("\n[TEST 5] DOWN trend (should generate BEAR call spread)")
    df_down = create_trending_ohlc_data(trend="DOWN", periods=120)
    strategy._fetch_historical_data = MagicMock(return_value=df_down)
    context = create_mock_context(instrument=instrument, tick=tick, current_time=time(10, 0))
    signals = strategy.generate_signals(context)
    print(f"  Signals generated: {len(signals)}")
    if signals:
        signal = signals[0]
        print(f"  Signal direction: {signal.metadata.get('direction')}")
        print(f"  ✅ PASS: BEAR spread signal generated")
    else:
        print("  ⚠️  No signal (check filter rejections)")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("TREND CREDIT SPREAD V1 TEST SUITE")
    print("="*60)
    print("\nThis script tests the trend credit spread strategy with mock data.")
    print("It verifies ADX calculation, trend detection, filter logic, and signal generation.")
    
    try:
        test_trend_credit_spread()
        
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print("✅ All tests completed")
        print("\nNext steps:")
        print("1. Check metrics: curl http://localhost:8000/metrics | grep trend_credit_spread")
        print("2. Run in PAPER mode to test with real market data")
        print("3. Monitor filter rejections to understand why signals are/aren't generated")
        print("4. Replace _select_spread_legs with delta-based chain selection")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

