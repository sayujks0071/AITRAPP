import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from packages.core.execution import ExecutionEngine, OrderResult
from packages.core.models import Order, OrderStatus, Signal, SignalSide, Instrument, InstrumentType
from packages.core.config import ExecutionConfig, Settings, AppMode

@pytest.mark.asyncio
async def test_execution_crash_on_missing_order():
    # Setup mocks
    mock_kite = MagicMock()
    mock_config = ExecutionConfig({
        "max_order_retries": 1,
        "retry_backoff_ms": 10,
        "tops_cap_per_sec": 5
    })
    mock_settings = MagicMock()
    mock_settings.app_mode.value = "LIVE"
    mock_settings.kite_api_key = "test_key"
    mock_settings.kite_access_token = "test_token"

    engine = ExecutionEngine(mock_kite, mock_config, mock_settings)

    # Create a dummy signal
    instrument = Instrument(
        token=123,
        symbol="TEST",
        tradingsymbol="TEST",
        exchange="NSE",
        instrument_type=InstrumentType.EQ
    )

    signal = Signal(
        strategy_name="TestStrategy",
        timestamp=datetime.now(),
        instrument=instrument,
        side=SignalSide.LONG,
        entry_price=100.0,
        stop_loss=90.0
    )

    # Mock _place_entry_order to return an order
    entry_order = Order(
        order_id="order_123",
        client_order_id="co_123",
        timestamp=datetime.now(),
        instrument=instrument,
        side="BUY",
        quantity=10,
        price=100.0,
        order_type="LIMIT",
        product="MIS",
        status=OrderStatus.OPEN,
        strategy_name="TestStrategy"
    )

    engine._place_entry_order = AsyncMock(return_value=entry_order)

    # Mock _wait_for_fill to return False (timeout)
    engine._wait_for_fill = AsyncMock(return_value=False)

    # Mock cancel_order to succeed
    engine.cancel_order = AsyncMock(return_value=True)

    # Mock _place_exit_orders
    engine._place_exit_orders = AsyncMock()

    # Setup orders map behavior
    # 1. First call (before cancel): returns order with partial fill
    order_before_cancel = Order(
        order_id="order_123",
        client_order_id="co_123",
        timestamp=datetime.now(),
        instrument=instrument,
        side="BUY",
        quantity=10,
        price=100.0,
        order_type="LIMIT",
        product="MIS",
        status=OrderStatus.OPEN,
        filled_quantity=5, # Partial fill
        strategy_name="TestStrategy"
    )

    # 2. Second call (after cancel): returns None (simulating order disappearance)

    # We need to mock self.orders.get
    # Since self.orders is a dict, we can't easily mock get on it directly if we use the real dict.
    # But we can patch the dict access or just manipulate it.

    # However, the code uses `self.orders.get(order_id)`.
    # Let's mock the `orders` attribute of engine to be a MagicMock that behaves like a dict but we control `get`.

    engine.orders = MagicMock()

    def get_side_effect(order_id):
        if order_id == "order_123":
            # We need to return different values based on call count or state
            # But the logic in execute_signal calls get() multiple times.

            # Sequence in execute_signal:
            # 1. _place_entry_order returns entry_order (we mocked this)
            # 2. _wait_for_fill (mocked to False)
            # 3. current_order = self.orders.get(entry_order.order_id) -> Should return order_before_cancel
            # 4. cancel_order
            # 5. entry_order = self.orders.get(entry_order.order_id) -> Should return None

            if engine.orders.get.call_count == 1:
                return order_before_cancel
            else:
                return None
        return None

    engine.orders.get.side_effect = get_side_effect

    # Also need to make sure _place_entry_order returns the order object that has the ID we expect
    # The code does: entry_order = await self._place_entry_order(...)
    # Then uses entry_order.client_order_id and entry_order.order_id

    # Run execute_signal
    # We expect this to return OrderResult.PARTIAL even if the order object is missing from map after refresh,
    # because we detected partial fill before cancellation.
    # Currently it catches AttributeError and returns OrderResult.ERROR

    result, order = await engine.execute_signal(signal, quantity=10, wait_for_fill=True, place_exits=True)

    # Check if we got PARTIAL result
    assert result == OrderResult.PARTIAL, f"Expected PARTIAL, got {result}"

    # We also expect exit orders to be attempted for the filled quantity (5)
    # But since entry_order was None, _place_exit_orders might not have been called or failed.
    # We want to ensure it IS called with the valid order object we had.

    # Verify _place_exit_orders was called
    assert engine._place_exit_orders.called, "_place_exit_orders should be called"

    # Verify the arguments passed to _place_exit_orders
    # args: (signal, entry_order, quantity)
    args = engine._place_exit_orders.call_args[0]
    assert args[1] is not None, "Should pass a valid order object to _place_exit_orders"
    assert args[2] == 5, "Should place exits for filled quantity (5)"

if __name__ == "__main__":
    # Manually run the test function if executed as a script
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_execution_crash_on_missing_order())
    print("Test finished")
