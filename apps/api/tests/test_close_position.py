import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
from packages.core.models import Position, PositionStatus, Instrument, InstrumentType, SignalSide, Order
from apps.api.state import AppState

@pytest.fixture
def mock_app_state():
    # Mock settings and config
    settings = MagicMock()
    config = MagicMock()
    config.mode = "PAPER"
    config.risk.capital_base = 100000
    config.strategies = []
    config.universe = []
    config.execution = MagicMock()
    config.ranking = MagicMock()
    config.exits = MagicMock()

    state = AppState(settings, config)

    # Mock components
    state.execution_engine = AsyncMock()
    state.exit_manager = MagicMock()
    state.instrument_manager = AsyncMock()
    state.market_data_stream = MagicMock()

    return state

@pytest.fixture
def sample_position():
    instrument = Instrument(
        token=123,
        symbol="TEST",
        tradingsymbol="TEST",
        exchange="NSE",
        instrument_type=InstrumentType.EQ
    )
    return Position(
        position_id="pos_123",
        instrument=instrument,
        entry_time=datetime.now(),
        entry_price=100.0,
        quantity=10,
        side=SignalSide.LONG,
        current_price=110.0
    )

@pytest.mark.asyncio
async def test_close_position_success(mock_app_state, sample_position):
    # Setup
    mock_app_state.positions = {sample_position.position_id: sample_position}

    mock_order = Order(
        order_id="ord_1",
        client_order_id="cl_1",
        timestamp=datetime.now(),
        instrument=sample_position.instrument,
        side="SELL",
        quantity=10,
        price=0,
        order_type="MARKET",
        product="MIS",
        status="COMPLETE",
        average_price=110.0
    )
    mock_app_state.execution_engine.close_position.return_value = mock_order

    # Execute
    result = await mock_app_state.close_position_by_token(123)

    # Verify response
    assert result.status == "CLOSED"
    assert result.position_id == "pos_123"
    assert result.order_id == "ord_1"
    assert result.average_price == 110.0

    # Verify side effects
    mock_app_state.execution_engine.close_position.assert_called_once_with(sample_position, reason="MANUAL")
    mock_app_state.exit_manager.on_position_closed.assert_called_once_with("pos_123")
    assert sample_position.status == PositionStatus.CLOSED
    assert sample_position.realized_pnl == 100.0  # (110 - 100) * 10

@pytest.mark.asyncio
async def test_close_position_not_found(mock_app_state):
    result = await mock_app_state.close_position_by_token(999)

    assert result.status == "NOT_FOUND"
    assert "not found" in result.reason
    mock_app_state.execution_engine.close_position.assert_not_called()

@pytest.mark.asyncio
async def test_close_position_already_closed(mock_app_state, sample_position):
    sample_position.status = PositionStatus.CLOSED
    mock_app_state.positions = {sample_position.position_id: sample_position}

    result = await mock_app_state.close_position_by_token(123)

    assert result.status == "ALREADY_CLOSED"
    mock_app_state.execution_engine.close_position.assert_not_called()

@pytest.mark.asyncio
async def test_close_position_rejected(mock_app_state, sample_position):
    mock_app_state.positions = {sample_position.position_id: sample_position}
    mock_app_state.execution_engine.close_position.return_value = None

    result = await mock_app_state.close_position_by_token(123)

    assert result.status == "REJECTED"
    assert result.reason == "Order placement failed"
    mock_app_state.exit_manager.on_position_closed.assert_not_called()
    assert sample_position.status == PositionStatus.OPEN
