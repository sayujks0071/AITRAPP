import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from packages.core.execution import ExecutionEngine, OrderResult, OrderStatus, SignalSide
from packages.core.models import Signal, Instrument, InstrumentType, Order
from packages.core.config import ExecutionConfig, Settings

@pytest.fixture
def mock_kite():
    kite = MagicMock()
    kite.place_order.return_value = {"order_id": "123456"}
    return kite

@pytest.fixture
def mock_config():
    config_dict = {
        "max_order_retries": 1,
        "retry_backoff_ms": 10,
        "default_order_type": "MARKET",
        "tops_cap_per_sec": 10
    }
    return ExecutionConfig(config_dict)

@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setenv("APP_MODE", "LIVE")
    return Settings()

@pytest.fixture
def execution_engine(mock_kite, mock_config, mock_settings):
    engine = ExecutionEngine(mock_kite, mock_config, mock_settings)
    engine.is_paper_mode = False
    engine.kite.access_token = "valid_token"
    return engine

@pytest.fixture
def mock_signal():
    instrument = Instrument(
        token=123,
        symbol="INFY",
        tradingsymbol="INFY",
        exchange="NSE",
        instrument_type=InstrumentType.EQ,
        lot_size=1
    )
    return Signal(
        strategy_name="TEST_STRAT",
        timestamp=datetime.now(),
        instrument=instrument,
        side=SignalSide.LONG,
        entry_price=100.0,
        stop_loss=90.0,
        take_profit_1=110.0
    )

@pytest.mark.asyncio
async def test_non_blocking_execution_does_not_timeout_or_double_place(execution_engine, mock_signal):
    """
    Test that execute_signal with wait_for_fill=False:
    1. Returns immediately (no timeout/blocking).
    2. Returns PLACED result.
    3. Does NOT place exit orders.
    """
    quantity = 10

    # Run execution with new flags
    result, order = await execution_engine.execute_signal(
        mock_signal,
        quantity,
        wait_for_fill=False,
        place_exits=False
    )

    # 1. Verify result
    assert result == OrderResult.PLACED
    assert order is not None
    assert order.status == OrderStatus.PENDING

    # 2. Verify only Entry order placed (no SL/TP)
    # entry order id 123456
    assert execution_engine.kite.place_order.call_count == 1

    # 3. Verify cancel was NOT called (no timeout)
    execution_engine.kite.cancel_order.assert_not_called()

@pytest.mark.asyncio
async def test_update_order_status_logic(execution_engine):
    """Test update_order_status method"""

    # Setup an order in memory
    order = Order(
        order_id="123",
        client_order_id="CO_123",
        timestamp=datetime.now(),
        instrument=None,
        side="BUY",
        quantity=10,
        price=100.0,
        order_type="MARKET",
        product="MIS",
        status=OrderStatus.PENDING
    )
    execution_engine.orders["123"] = order
    execution_engine.order_id_map["CO_123"] = "123"

    fill_event = {
        "client_order_id": "CO_123",
        "filled_qty": 10,
        "average_price": 100.5
    }

    execution_engine.update_order_status(fill_event)

    assert order.status == OrderStatus.COMPLETE
    assert order.filled_quantity == 10
    assert order.average_price == 100.5
