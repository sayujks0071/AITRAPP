#!/usr/bin/env python3
"""
Test script to verify sibling order cancellation on exit.

Tests that ExecutionEngine.close_position cancels any open/trigger-pending
orders for the same symbol before submitting the market exit.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Set MOCK_KITE before imports
os.environ["MOCK_KITE"] = "1"
os.environ["APP_MODE"] = "PAPER"

from packages.core.mock_adapter import MockKite
from packages.core.execution.execution_engine import ExecutionEngine, ExecutionConfig
from packages.core.models import Instrument, InstrumentType, Position, SignalSide, PositionStatus
from packages.core.rate_limiter import LeakyBucketLimiter
from packages.core.compliance import ComplianceGuard


class TestableMockKite(MockKite):
    """Extended MockKite that allows creating orders with specific statuses"""
    
    def __init__(self, default_ltp: float = 100.0):
        super().__init__(default_ltp)
        self._order_id_seq = 0
    
    async def place_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "LIMIT",
        price: Optional[float] = None,
        product: str = "NRML",
        variety: str = "regular",
        tag: Optional[str] = None,
        status: Optional[str] = None,  # Allow setting status
        **kwargs
    ) -> str:
        self._order_id_seq += 1
        oid = f"MOCK_{self._order_id_seq}"
        fill_price = price if price is not None else self._ltp_value
        now = time.time()
        
        # Use provided status or default to COMPLETE
        order_status = status if status else "COMPLETE"
        
        order = {
            "order_id": oid,
            "tradingsymbol": symbol,
            "symbol": symbol,
            "transaction_type": side,
            "quantity": quantity,
            "filled_quantity": 0 if order_status in ("OPEN", "TRIGGER PENDING") else quantity,
            "average_price": fill_price if order_status == "COMPLETE" else 0.0,
            "price": price,
            "status": order_status,
            "variety": variety,
            "product": product,
            "order_type": order_type,
            "tag": tag,
            "created_at": now,
            "updated_at": now,
        }
        self._orders[oid] = order
        
        # Only update positions if order is COMPLETE
        if order_status == "COMPLETE":
            pos = self._positions.get(symbol, {"symbol": symbol, "quantity": 0, "avg_price": 0.0})
            qty = pos["quantity"]
            if side.upper() == "BUY":
                new_qty = qty + quantity
            else:
                new_qty = qty - quantity
            pos["quantity"] = new_qty
            pos["avg_price"] = fill_price
            self._positions[symbol] = pos
        
        return oid


async def test_sibling_order_cancellation():
    """Test that close_position cancels sibling orders"""
    print("🧪 Testing Sibling Order Cancellation on Exit")
    print("=" * 60)
    
    # Setup
    print("\n1️⃣  Setting up MockKite and ExecutionEngine...")
    mock_kite = TestableMockKite(default_ltp=24000.0)
    mock_kite.set_ltp(24000.0)
    
    rate_limiter = LeakyBucketLimiter(rate_per_second=10.0, rate_per_minute=300.0, bucket_size=20)
    compliance_guard = ComplianceGuard(rate_limiter, lambda: False)
    
    config = ExecutionConfig(dry_run=False)
    engine = ExecutionEngine(
        kite_client=mock_kite,
        config=config,
        rate_limiter=rate_limiter,
        compliance_guard=compliance_guard
    )
    print("   ✅ Setup complete")
    
    # Create instrument
    symbol = "NIFTY 50"
    instrument = Instrument(
        token=256265,
        symbol=symbol,
        tradingsymbol=symbol,
        exchange="NSE",
        instrument_type=InstrumentType.EQ
    )
    
    # Step 1: Place entry order (fills immediately)
    print(f"\n2️⃣  Placing entry order for {symbol}...")
    entry_order_id = await mock_kite.place_order(
        symbol=symbol,
        side="BUY",
        quantity=50,
        order_type="MARKET",
        price=24000.0,
        status="COMPLETE",  # Entry fills immediately
        tag="ENTRY"
    )
    print(f"   ✅ Entry order placed: {entry_order_id}")
    
    # Step 2: Place SL and TP orders (open/trigger-pending)
    print(f"\n3️⃣  Placing SL and TP orders (should be cancelled on exit)...")
    sl_order_id = await mock_kite.place_order(
        symbol=symbol,
        side="SELL",
        quantity=50,
        order_type="SL",
        price=23800.0,  # Stop loss
        status="OPEN",  # Still open
        tag="STOP_LOSS"
    )
    tp_order_id = await mock_kite.place_order(
        symbol=symbol,
        side="SELL",
        quantity=50,
        order_type="LIMIT",
        price=24200.0,  # Take profit
        status="TRIGGER PENDING",  # Trigger pending
        tag="TAKE_PROFIT"
    )
    print(f"   ✅ SL order placed: {sl_order_id} (status: OPEN)")
    print(f"   ✅ TP order placed: {tp_order_id} (status: TRIGGER PENDING)")
    
    # Verify orders exist
    all_orders = await mock_kite.orders()
    open_orders = [o for o in all_orders if o["status"] in ("OPEN", "TRIGGER PENDING")]
    print(f"\n   📊 Open/Trigger-pending orders before exit: {len(open_orders)}")
    for order in open_orders:
        print(f"      - {order['order_id']}: {order['tag']} ({order['status']})")
    
    # Step 3: Create position object
    print(f"\n4️⃣  Creating position object...")
    position = Position(
        instrument=instrument,
        side=SignalSide.LONG,
        quantity=50,
        entry_price=24000.0,
        current_price=24000.0,
        status=PositionStatus.OPEN
    )
    print(f"   ✅ Position created: {position.side.value} {position.quantity} @ {position.entry_price}")
    
    # Step 4: Close position (should cancel sibling orders)
    print(f"\n5️⃣  Closing position (should cancel SL/TP orders)...")
    exit_result = await engine.close_position(position, reason="TEST_EXIT")
    
    if exit_result.success:
        print(f"   ✅ Exit order placed: {exit_result.order_id}")
    else:
        print(f"   ❌ Exit failed: {exit_result.error_message}")
        return False
    
    # Step 5: Verify sibling orders were cancelled
    print(f"\n6️⃣  Verifying sibling orders were cancelled...")
    all_orders_after = await mock_kite.orders()
    open_orders_after = [o for o in all_orders_after if o["status"] in ("OPEN", "TRIGGER PENDING")]
    cancelled_orders = [o for o in all_orders_after if o["status"] == "CANCELLED" and o["order_id"] in [sl_order_id, tp_order_id]]
    
    print(f"   📊 Open/Trigger-pending orders after exit: {len(open_orders_after)}")
    for order in open_orders_after:
        print(f"      - {order['order_id']}: {order['tag']} ({order['status']})")
    
    print(f"   📊 Cancelled SL/TP orders: {len(cancelled_orders)}")
    for order in cancelled_orders:
        print(f"      - {order['order_id']}: {order['tag']} ({order['status']})")
    
    # Assertions
    success = True
    if len(open_orders_after) > 0:
        # Check if any open orders are for the same symbol
        same_symbol_open = [o for o in open_orders_after if o.get("tradingsymbol") == symbol or o.get("symbol") == symbol]
        if same_symbol_open:
            print(f"\n   ❌ FAIL: Found {len(same_symbol_open)} open orders for {symbol} after exit!")
            for order in same_symbol_open:
                print(f"      - {order['order_id']}: {order['tag']} ({order['status']})")
            success = False
        else:
            print(f"\n   ✅ PASS: No open orders for {symbol} after exit")
    else:
        print(f"\n   ✅ PASS: No open orders remaining")
    
    if len(cancelled_orders) == 2:
        print(f"   ✅ PASS: Both SL and TP orders were cancelled")
    else:
        print(f"\n   ⚠️  WARNING: Expected 2 cancelled orders, found {len(cancelled_orders)}")
        if len(cancelled_orders) < 2:
            success = False
    
    return success


if __name__ == "__main__":
    import time
    from typing import Optional
    
    try:
        result = asyncio.run(test_sibling_order_cancellation())
        if result:
            print("\n" + "=" * 60)
            print("✅ TEST PASSED: Sibling order cancellation works correctly")
            print("=" * 60)
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("❌ TEST FAILED: Sibling orders were not cancelled")
            print("=" * 60)
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

