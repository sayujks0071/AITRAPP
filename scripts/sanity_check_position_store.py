#!/usr/bin/env python3
"""Sanity check position store with single-trade round-trip test"""
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.position_store import PositionStore
from packages.core.models import Position, Instrument, SignalSide, PositionStatus, InstrumentType


def test_position_store_round_trip():
    """Test position store with a single round-trip trade"""
    print("🧪 Position Store Sanity Check")
    print("=" * 60)
    print()
    
    # Initialize position store
    store = PositionStore()
    print("✅ Position store initialized")
    
    # Create a test position (1 lot NIFTY CE sold - short option)
    test_instrument = Instrument(
        token=12345,
        symbol="NIFTY",
        tradingsymbol="NIFTY25JAN25000CE",
        exchange="NFO",
        instrument_type=InstrumentType.CE,
        expiry=datetime(2025, 1, 25),
        strike=25000.0,
        lot_size=50,
        tick_size=0.05,
    )
    
    test_position = Position(
        position_id="test_pos_001",
        instrument=test_instrument,
        entry_time=datetime.now(),
        entry_price=150.0,  # Premium received
        quantity=50,  # 1 lot
        side=SignalSide.SHORT,  # Short option
        current_price=150.0,
        stop_loss=200.0,
        risk_amount=2500.0,  # Max loss estimate
        strategy_name="test_strategy",
    )
    
    print("\n📝 Step 1: Add position")
    print("-" * 60)
    store.add_position(test_position)
    print(f"   Position ID: {test_position.position_id}")
    print(f"   Symbol: {test_position.instrument.tradingsymbol}")
    print(f"   Side: {test_position.side.value}")
    print(f"   Quantity: {test_position.quantity}")
    print(f"   Entry Price: {test_position.entry_price}")
    print(f"   Strategy: {test_position.strategy_name}")
    
    # Check position exists
    open_positions = store.get_open_positions(strategy_name="test_strategy")
    if len(open_positions) != 1:
        print(f"❌ Expected 1 open position, got {len(open_positions)}")
        return False
    print("✅ Position added successfully")
    
    # Check short premium notional
    print("\n📊 Step 2: Check short premium notional")
    print("-" * 60)
    short_notional = store.aggregate_short_premium_notional(
        strategies={"test_strategy"},
        underlying="NIFTY"
    )
    expected_notional = test_position.entry_price * test_position.quantity
    print(f"   Short premium notional: {short_notional:.2f}")
    print(f"   Expected: {expected_notional:.2f}")
    
    if abs(short_notional - expected_notional) > 0.01:
        print(f"❌ Notional mismatch! Expected {expected_notional}, got {short_notional}")
        return False
    print("✅ Short premium notional correct")
    
    # Update position with price move
    print("\n📈 Step 3: Update position (price move)")
    print("-" * 60)
    new_price = 120.0  # Option price dropped (good for short position)
    store.update_position(test_position.position_id, new_price)
    
    updated_position = store.positions.get(test_position.position_id)
    if not updated_position:
        print("❌ Position not found after update")
        return False
    
    updated_position.update_pnl()
    unrealized_pnl = updated_position.unrealized_pnl
    
    # For short position: PnL = (entry_price - current_price) * quantity
    expected_pnl = (test_position.entry_price - new_price) * test_position.quantity
    print(f"   Current price: {new_price}")
    print(f"   Unrealized PnL: {unrealized_pnl:.2f}")
    print(f"   Expected PnL: {expected_pnl:.2f}")
    
    if abs(unrealized_pnl - expected_pnl) > 0.01:
        print(f"❌ PnL mismatch! Expected {expected_pnl}, got {unrealized_pnl}")
        return False
    print("✅ Unrealized PnL correct")
    
    # Check strategy exposure
    print("\n📊 Step 4: Check strategy exposure")
    print("-" * 60)
    exposure = store.get_strategy_exposure("test_strategy")
    print(f"   Total notional: {exposure.total_notional:.2f}")
    print(f"   Short premium notional: {exposure.short_premium_notional:.2f}")
    print(f"   Long premium notional: {exposure.long_premium_notional:.2f}")
    print(f"   Num positions: {exposure.num_positions}")
    print(f"   Unrealized PnL: {exposure.unrealized_pnl:.2f}")
    
    if exposure.short_premium_notional != expected_notional:
        print(f"❌ Exposure notional mismatch!")
        return False
    if exposure.unrealized_pnl != unrealized_pnl:
        print(f"❌ Exposure PnL mismatch!")
        return False
    print("✅ Strategy exposure correct")
    
    # Close position
    print("\n🔒 Step 5: Close position")
    print("-" * 60)
    exit_price = 100.0  # Option expired worthless (best case for short)
    exit_time = datetime.now()
    store.close_position(test_position.position_id, exit_price, exit_time)
    
    closed_position = store.positions.get(test_position.position_id)
    if not closed_position:
        print("❌ Position not found after close")
        return False
    
    if closed_position.status != PositionStatus.CLOSED:
        print(f"❌ Position status should be CLOSED, got {closed_position.status}")
        return False
    
    # For short position: Realized PnL = (entry_price - exit_price) * quantity
    expected_realized = (test_position.entry_price - exit_price) * test_position.quantity
    actual_realized = closed_position.realized_pnl or 0.0
    
    print(f"   Exit price: {exit_price}")
    print(f"   Realized PnL: {actual_realized:.2f}")
    print(f"   Expected PnL: {expected_realized:.2f}")
    
    if abs(actual_realized - expected_realized) > 0.01:
        print(f"❌ Realized PnL mismatch! Expected {expected_realized}, got {actual_realized}")
        return False
    print("✅ Position closed, realized PnL correct")
    
    # Check position is no longer in open positions
    open_positions_after = store.get_open_positions(strategy_name="test_strategy")
    if len(open_positions_after) != 0:
        print(f"❌ Expected 0 open positions after close, got {len(open_positions_after)}")
        return False
    print("✅ Position removed from open positions")
    
    # Check stats
    print("\n📈 Step 6: Check strategy stats")
    print("-" * 60)
    stats = store.get_strategy_stats("test_strategy", trade_window=10, day_window=30)
    print(f"   Hit rate: {stats['hit_rate']:.2f}")
    print(f"   Expectancy: {stats['expectancy_perc']:.4f}")
    print(f"   Num trades: {stats['num_trades_window']}")
    
    if stats['num_trades_window'] != 1:
        print(f"❌ Expected 1 trade in stats, got {stats['num_trades_window']}")
        return False
    
    # Check realized PnL tracking
    realized_pnl = store.realized_pnl_by_strategy.get("test_strategy", 0.0)
    print(f"   Cumulative realized PnL: {realized_pnl:.2f}")
    
    if abs(realized_pnl - expected_realized) > 0.01:
        print(f"❌ Cumulative PnL mismatch!")
        return False
    print("✅ Strategy stats correct")
    
    print("\n" + "=" * 60)
    print("✅ ALL CHECKS PASSED - Position store is sane!")
    print("=" * 60)
    print()
    print("💡 Your position store is ready to use for:")
    print("   - Allocator performance stats")
    print("   - H1 short premium / tail notional")
    print("   - G1/T1/D1 book PnL")
    print("   - Daily reports")
    print()
    
    return True


def main():
    """Run position store sanity check"""
    try:
        success = test_position_store_round_trip()
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Error during sanity check: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


