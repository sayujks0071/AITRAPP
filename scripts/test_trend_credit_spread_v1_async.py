#!/usr/bin/env python3
"""
Async Test Script for Trend Credit Spread V1 Strategy

This script tests the trend credit spread strategy with mock data,
matching AITRAPP's actual implementation patterns.

Usage:
    python3 scripts/test_trend_credit_spread_v1_async.py
"""

import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

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


def create_trending_ohlc_data(trend: str = "UP", periods: int = 200) -> pd.DataFrame:
    """
    Create mock OHLC data with clear trend and ADX > threshold.
    
    Generates data with strong directional movement to ensure ADX > 20.
    
    Args:
        trend: "UP" or "DOWN"
        periods: Number of 5-minute bars
    """
    dates = pd.date_range(end=datetime.now(), periods=periods, freq="5min")
    
    if trend == "UP":
        # Strong uptrend with consistent higher highs and higher lows
        base = 20000
        close = pd.Series([base + i * 2.5 + (i % 10) * 0.5 for i in range(periods)])
        # Higher highs
        high = close + 5 + pd.Series([(i % 5) * 0.3 for i in range(periods)])
        # Higher lows
        low = close - 3 - pd.Series([(i % 5) * 0.2 for i in range(periods)])
    else:
        # Strong downtrend with consistent lower highs and lower lows
        base = 20000
        close = pd.Series([base - i * 2.5 - (i % 10) * 0.5 for i in range(periods)])
        # Lower highs
        high = close + 3 + pd.Series([(i % 5) * 0.2 for i in range(periods)])
        # Lower lows
        low = close - 5 - pd.Series([(i % 5) * 0.3 for i in range(periods)])
    
    open_price = close - 1
    
    df = pd.DataFrame({
        "open": open_price.values,
        "high": high.values,
        "low": low.values,
        "close": close.values
    }, index=dates)
    
    return df


def test_strategy():
    """Test Trend Credit Spread V1 with mock data"""
    print("🧪 STARTING TREND SPREAD TEST...")
    
    # Mock Config
    MOCK_CONFIG = {
        "enabled": True,
        "underlying": "NIFTY",
        "underlying_token": 256265,  # NIFTY spot token
        "lot_size": 25,
        "entry_time": "09:30",
        "exit_time": "15:15",
        "adx_period": 14,
        "adx_threshold": 20.0,
        "ema_fast_period": 10,  # Short for testing
        "ema_slow_period": 20,
        "min_credit": 500,
        "wing_width_pts": 200,
        "max_loss_rs": 3000,
        "target_profit_pct": 0.5,
        "max_positions": 1,
        "max_lot_size": 1,
        "instruments": ["NIFTY"],
    }
    
    # 1. Mock Kite Client
    mock_kite = MagicMock()
    mock_kite_client = MagicMock()
    mock_kite_client.kite = mock_kite
    
    # Generate UP TREND data
    df_up = create_trending_ohlc_data(trend="UP", periods=200)
    
    # Mock historical_data (Kite API format)
    # Kite returns list of dicts with 'date', 'open', 'high', 'low', 'close', 'volume', 'oi'
    historical_data = []
    for idx, row in df_up.iterrows():
        historical_data.append({
            'date': idx,
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': 1000000,
            'oi': 0
        })
    
    mock_kite.historical_data = MagicMock(return_value=historical_data)
    
    # 2. Mock Instrument Manager
    mock_instrument_manager = MagicMock()
    # Add some mock option instruments for spread leg selection
    mock_instrument_manager._instruments = {}
    
    # Create mock option instruments for Bull Put Spread
    # Short leg: 19800PE
    short_leg = Instrument(
        token=123456,
        symbol="NIFTY",
        tradingsymbol="NIFTY24NOV19800PE",
        exchange="NFO",
        instrument_type=InstrumentType.PE,
        expiry=datetime.now().date() + timedelta(days=7),
        strike=19800,
        lot_size=25,
        tick_size=0.05
    )
    
    # Long leg: 19600PE
    long_leg = Instrument(
        token=123457,
        symbol="NIFTY",
        tradingsymbol="NIFTY24NOV19600PE",
        exchange="NFO",
        instrument_type=InstrumentType.PE,
        expiry=datetime.now().date() + timedelta(days=7),
        strike=19600,
        lot_size=25,
        tick_size=0.05
    )
    
    mock_instrument_manager._instruments[123456] = short_leg
    mock_instrument_manager._instruments[123457] = long_leg
    
    # 3. Init Strategy
    strat = TrendCreditSpreadV1(
        name="trend_credit_spread_v1",
        params=MOCK_CONFIG,
        instrument_manager=mock_instrument_manager,
        risk_engine=MagicMock(),
        metrics=None,
        kite_client=mock_kite_client,
        position_store=None
    )
    
    # Set underlying token
    strat.underlying_token = 256265
    
    # 4. Create StrategyContext for entry scan
    print("... Simulating Entry Scan (09:45) ...")
    instrument = create_mock_instrument()
    tick = create_mock_tick(price=20000.0)
    scan_time = datetime.now().replace(hour=9, minute=45, second=0, microsecond=0)
    
    context = StrategyContext(
        timestamp=scan_time,
        instrument=instrument,
        latest_tick=tick,
        bars_1s=[],
        bars_5s=[],
        net_liquid=1000000.0,
        available_margin=700000.0,
        open_positions=0,
        iv_percentile=0.50
    )
    
    # Mock the _fetch_historical_data method to return our mock data
    # Also need to ensure the data has enough periods for ADX calculation
    df_up = create_trending_ohlc_data(trend="UP", periods=200)
    
    with patch.object(strat, '_fetch_historical_data', return_value=df_up):
        # Also mock _get_option_credit to return valid credit for testing
        with patch.object(strat, '_get_option_credit', return_value=1200.0):
            signals = strat.generate_signals(context)
    
    # Assertions
    if signals and len(signals) > 0:
        signal = signals[0]
        print(f"✅ Entry Successful! Generated {len(signals)} signal(s).")
        print(f"   Direction: {signal.metadata.get('direction')}")
        print(f"   Structure: {signal.metadata.get('structure')}")
        print(f"   Credit Collected: ₹{signal.metadata.get('credit_collected', 0):.2f}")
        print(f"   ADX Value: {signal.metadata.get('adx_value', 0):.2f}")
        print(f"   Trend: {signal.metadata.get('trend')}")
    else:
        print("❌ Entry Failed - No signals generated.")
        print("   Check filter rejections in logs above.")
    
    # 5. Simulate position opened (manually set state for testing)
    if signals and len(signals) > 0:
        strat.position_open = True
        strat.spread_direction = signal.metadata.get('direction')
        strat.entry_credit_rs = signal.metadata.get('credit_collected', 0)
        strat.target_profit_rs = strat.entry_credit_rs * strat.target_profit_pct
        strat.stop_loss_rs = strat.max_loss_rs
        strat.short_leg_instrument = short_leg
        strat.long_leg_instrument = long_leg
        
        # 6. Run Management Scan (Profit Scenario)
        print("\n... Simulating Management Scan (10:00 - Profit Scenario) ...")
        management_time = scan_time + timedelta(minutes=15)
        context.timestamp = management_time
        
        # Mock credit calculation to show profit (credit decreased)
        # In real scenario, this would fetch current option prices
        # For test: simulate that credit decreased by 60% (profit)
        original_credit = strat.entry_credit_rs
        current_credit = original_credit * 0.4  # 60% profit
        
        # Mock _get_option_credit to return profitable credit
        with patch.object(strat, '_get_option_credit', return_value=current_credit):
            exit_signals = strat._manage_exit(context)
        
        if not strat.position_open:
            print("✅ Management Successful! Position Closed on Target Profit.")
            print(f"   Entry Credit: ₹{original_credit:.2f}")
            print(f"   Current Credit: ₹{current_credit:.2f}")
            print(f"   Profit: ₹{original_credit - current_credit:.2f}")
        else:
            print("⚠️  Position still open (may need more profit or different scenario)")
    
    # 7. Test Hard Exit Time
    print("\n... Simulating Hard Exit Time (15:20) ...")
    strat.position_open = True  # Reset for hard exit test
    hard_exit_time = datetime.now().replace(hour=15, minute=20, second=0, microsecond=0)
    context.timestamp = hard_exit_time
    
    exit_signals = strat.generate_signals(context)
    
    if not strat.position_open:
        print("✅ Hard Exit Successful! Position Closed at exit time.")
    else:
        print("❌ Hard Exit Failed. Position still open.")
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print("✅ All test scenarios completed")
    print("\nNext steps:")
    print("1. Test with real market data in PAPER mode")
    print("2. Monitor metrics: curl http://localhost:8000/metrics | grep trend_credit_spread")
    print("3. Replace _select_spread_legs with delta-based chain selection")


if __name__ == "__main__":
    test_strategy()

