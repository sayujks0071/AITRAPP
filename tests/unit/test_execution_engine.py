import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from packages.core.execution import ExecutionEngine, OrderResult, OrderStatus, SignalSide
from packages.core.models import Signal, Instrument, InstrumentType, Order
from packages.core.config import ExecutionConfig, Settings, AppMode

@pytest.fixture
def mock_kite():
    return MagicMock()

@pytest.fixture
def mock_config():
    config_dict = {
        "max_order_retries": 3,
        "retry_backoff_ms": 100,
        "default_order_type": "MARKET",
        "tops_cap_per_sec": 10
    }
    return ExecutionConfig(config_dict)

@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setenv("KITE_API_KEY", "test_key")
    monkeypatch.setenv("KITE_API_SECRET", "test_secret")
    monkeypatch.setenv("KITE_ACCESS_TOKEN", "test_token")
    monkeypatch.setenv("KITE_USER_ID", "test_user")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("API_SECRET_KEY", "test_secret_key")
    monkeypatch.setenv("APP_MODE", "PAPER")
    return Settings()

@pytest.fixture
def execution_engine(mock_kite, mock_config, mock_settings):
    return ExecutionEngine(mock_kite, mock_config, mock_settings)

@pytest.fixture
def mock_signal():
    instrument = Instrument(
        token=123,
        symbol="INFY",
        tradingsymbol="INFY",
        exchange="NSE",
        instrument_type=InstrumentType.EQ
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
async def test_execute_signal_success(execution_engine, mock_signal):
    quantity = 10
    with patch.object(execution_engine, '_place_entry_order', new_callable=AsyncMock) as mock_place_entry:
        mock_entry_order = Order(
            order_id="123",
            client_order_id="CO_123",
            timestamp=datetime.now(),
            instrument=mock_signal.instrument,
            side="BUY",
            quantity=quantity,
            price=100.0,
            order_type="MARKET",
            product="MIS",
            status=OrderStatus.COMPLETE,
            filled_quantity=quantity,
            average_price=100.0
        )
        mock_place_entry.return_value = mock_entry_order
        # Populate internal state
        execution_engine.orders["123"] = mock_entry_order
        execution_engine.order_id_map["CO_123"] = "123"

        with patch.object(execution_engine, '_wait_for_fill', new_callable=AsyncMock) as mock_wait:
            mock_wait.return_value = True
            with patch.object(execution_engine, '_place_exit_orders', new_callable=AsyncMock) as mock_place_exit:
                result, order = await execution_engine.execute_signal(mock_signal, quantity)
                assert result == OrderResult.SUCCESS
                assert order == mock_entry_order
                mock_place_entry.assert_called_once()
                mock_wait.assert_called_once()
                mock_place_exit.assert_called_once()

@pytest.mark.asyncio
async def test_execute_signal_entry_rejected(execution_engine, mock_signal):
    quantity = 10
    with patch.object(execution_engine, '_place_entry_order', new_callable=AsyncMock) as mock_place_entry:
        mock_place_entry.return_value = None
        result, order = await execution_engine.execute_signal(mock_signal, quantity)
        assert result == OrderResult.REJECTED
        assert order is None

@pytest.mark.asyncio
async def test_execute_signal_timeout(execution_engine, mock_signal):
    quantity = 10
    with patch.object(execution_engine, '_place_entry_order', new_callable=AsyncMock) as mock_place_entry:
        mock_entry_order = Order(
            order_id="123",
            client_order_id="CO_123",
            timestamp=datetime.now(),
            instrument=mock_signal.instrument,
            side="BUY",
            quantity=quantity,
            price=100.0,
            order_type="MARKET",
            product="MIS",
            status=OrderStatus.OPEN,
            filled_quantity=0  # NO FILL
        )
        mock_place_entry.return_value = mock_entry_order
        execution_engine.orders["123"] = mock_entry_order

        with patch.object(execution_engine, '_wait_for_fill', new_callable=AsyncMock) as mock_wait:
            mock_wait.return_value = False
            with patch.object(execution_engine, 'cancel_order', new_callable=AsyncMock) as mock_cancel:
                result, order = await execution_engine.execute_signal(mock_signal, quantity)
                assert result == OrderResult.TIMEOUT
                assert order == mock_entry_order
                mock_cancel.assert_called_once_with("CO_123")

@pytest.mark.asyncio
async def test_partial_fill_handling(execution_engine, mock_signal):
    """
    Test logic for partial fills.
    """
    quantity = 10
    filled_quantity = 5

    with patch.object(execution_engine, '_place_entry_order', new_callable=AsyncMock) as mock_place_entry:
        mock_entry_order = Order(
            order_id="123",
            client_order_id="CO_123",
            timestamp=datetime.now(),
            instrument=mock_signal.instrument,
            side="BUY",
            quantity=quantity,
            price=100.0,
            order_type="MARKET",
            product="MIS",
            status=OrderStatus.OPEN,
            filled_quantity=filled_quantity  # Partial fill
        )
        mock_place_entry.return_value = mock_entry_order
        # Important: Ensure the engine knows about this order
        execution_engine.orders["123"] = mock_entry_order

        with patch.object(execution_engine, '_wait_for_fill', new_callable=AsyncMock) as mock_wait:
            mock_wait.return_value = False # Timeout

            with patch.object(execution_engine, 'cancel_order', new_callable=AsyncMock) as mock_cancel:
                # Mock place exits to verify it IS called
                with patch.object(execution_engine, '_place_exit_orders', new_callable=AsyncMock) as mock_place_exit:

                    result, order = await execution_engine.execute_signal(mock_signal, quantity)

                    assert result == OrderResult.PARTIAL
                    assert order.filled_quantity == filled_quantity

                    mock_cancel.assert_called_once()

                    # Verify exits were placed for the FILLED quantity
                    mock_place_exit.assert_called_once_with(mock_signal, mock_entry_order, filled_quantity)
