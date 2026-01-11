
import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
from packages.core.execution import ExecutionEngine, OrderResult
from packages.core.models import (
    Signal, SignalSide, Instrument, InstrumentType, Order, OrderStatus
)
from packages.core.config import ExecutionConfig, Settings, AppMode

@pytest.fixture
def mock_kite():
    kite = MagicMock()
    kite.place_order.return_value = {"order_id": "123456"}
    return kite

@pytest.fixture
def execution_engine(mock_kite):
    config = ExecutionConfig({})
    settings = Settings(APP_MODE=AppMode.LIVE)
    engine = ExecutionEngine(mock_kite, config, settings)
    # Disable rate limiting for speed
    engine.min_order_interval = 0
    engine.tops_cap = 100
    return engine

@pytest.mark.asyncio
async def test_partial_fill_missing_exit_orders(execution_engine, mock_kite):
    """
    Test that a partial fill followed by a timeout results in NO exit orders being placed.
    This confirms the bug.
    """
    # Setup Signal
    instrument = Instrument(
        token=123,
        symbol="INFY",
        tradingsymbol="INFY",
        exchange="NSE",
        instrument_type=InstrumentType.EQ,
        lot_size=1
    )
    signal = Signal(
        strategy_name="TestStrategy",
        timestamp=datetime.now(),
        instrument=instrument,
        side=SignalSide.LONG,
        entry_price=100.0,
        stop_loss=90.0,
        take_profit_1=110.0
    )

    # Mock _wait_for_fill to timeout immediately but simulate partial fill

    # We mock _wait_for_fill to return False (timeout)
    # AND side_effect to update the internal order state

    async def mock_wait_return_false(*args, **kwargs):
        # Update the order to be partially filled
        # We need the order_id. The key in engine.orders is "123456" (from mock_kite)
        order = execution_engine.orders.get("123456")
        if order:
            order.filled_quantity = 50
            order.status = OrderStatus.OPEN # Still OPEN, not COMPLETE
        return False

    execution_engine._wait_for_fill = AsyncMock(side_effect=mock_wait_return_false)
    execution_engine.cancel_order = AsyncMock(return_value=True)

    result, order = await execution_engine.execute_signal(signal, quantity=100)

    # Assertions
    assert result == OrderResult.PARTIAL

    # Verify the order state was updated by our mock
    assert order.filled_quantity == 50

    # CRITICAL: Verify exit orders were placed (SL/TP)
    # kite.place_order should have been called 3 times (Entry + SL + TP1)
    # Signal has take_profit_1 set, so SL + TP1 should be placed.
    assert mock_kite.place_order.call_count == 3
