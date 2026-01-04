
import pytest
from unittest.mock import Mock, patch, MagicMock
from packages.storage.models import Order, OrderSideEnum, OrderTypeEnum, OrderStatusEnum
from packages.core.oco import OCOManager

class TestOCOSideBug:
    def test_child_order_sides_are_opposite_to_entry(self):
        # Mock KiteClient since OCOManager needs it
        kite_client = Mock()
        oco_manager = OCOManager(kite_client)

        # Create an Entry Order (LONG/BUY)
        entry_order = Order(
            client_order_id="ENTRY_123",
            symbol="NIFTY23OCTFUT",
            instrument_token=12345,
            side=OrderSideEnum.BUY,
            qty=50,
            order_type=OrderTypeEnum.MARKET,
            price=19500.0,
            status=OrderStatusEnum.FILLED,
            strategy_name="TEST_STRAT"
        )

        # Create OCO group with SL and TP
        group_id = oco_manager.create_oco_group(
            entry_order=entry_order,
            stop_price=19400.0,
            tp1_price=19600.0,
            tp2_price=19700.0
        )

        group = oco_manager.groups[group_id]

        # Verify Entry Order Side
        assert group.entry_order.side == OrderSideEnum.BUY

        # Verify Stop Order Side (Should be SELL, but bug makes it BUY)
        stop_order = group.stop_order
        print(f"Entry Side: {entry_order.side}")
        print(f"Stop Order Side: {stop_order.side}")

        # Assert the EXPECTED behavior (FAILING TEST if bug exists)
        # If entry is BUY, exit (stop) should be SELL
        assert stop_order.side == OrderSideEnum.SELL, f"Stop order side should be SELL, got {stop_order.side}"

        # Verify TP1 Side
        tp1_order = group.tp1_order
        assert tp1_order.side == OrderSideEnum.SELL, f"TP1 order side should be SELL, got {tp1_order.side}"

        # Verify TP2 Side
        tp2_order = group.tp2_order
        assert tp2_order.side == OrderSideEnum.SELL, f"TP2 order side should be SELL, got {tp2_order.side}"

    @patch('packages.storage.database.order_exists')
    @patch('packages.core.oco.get_db_session')
    def test_on_entry_fill_transaction_type_for_buy_entry(self, mock_db_session, mock_order_exists):
        """Test that on_entry_fill passes correct transaction_type to place_order for BUY entry"""
        # Setup mocks
        mock_order_exists.return_value = False
        mock_db = MagicMock()
        mock_db.__enter__ = Mock(return_value=mock_db)
        mock_db.__exit__ = Mock(return_value=False)
        mock_db_session.return_value = mock_db

        # Mock KiteClient
        kite_client = Mock()
        kite_client.place_order = Mock(return_value="BROKER_ORDER_123")
        oco_manager = OCOManager(kite_client)

        # Create a BUY entry order
        entry_order = Order(
            client_order_id="ENTRY_BUY",
            symbol="NIFTY23OCTFUT",
            instrument_token=12345,
            side=OrderSideEnum.BUY,
            qty=50,
            order_type=OrderTypeEnum.MARKET,
            price=19500.0,
            status=OrderStatusEnum.FILLED,
            strategy_name="TEST_STRAT"
        )

        # Create OCO group
        group_id = oco_manager.create_oco_group(
            entry_order=entry_order,
            stop_price=19400.0,
            tp1_price=19600.0,
            tp2_price=19700.0
        )

        # Call on_entry_fill
        oco_manager.on_entry_fill(group_id)

        # Verify place_order was called 3 times (stop, tp1, tp2)
        assert kite_client.place_order.call_count == 3

        # Get all calls to place_order
        calls = kite_client.place_order.call_args_list

        # Verify Stop Loss order - should use SELL transaction_type for BUY entry
        stop_call = calls[0]
        assert stop_call.kwargs['transaction_type'] == 'SELL', \
            f"Stop order for BUY entry should have transaction_type='SELL', got {stop_call.kwargs['transaction_type']}"

        # Verify TP1 order - should use SELL transaction_type for BUY entry
        tp1_call = calls[1]
        assert tp1_call.kwargs['transaction_type'] == 'SELL', \
            f"TP1 order for BUY entry should have transaction_type='SELL', got {tp1_call.kwargs['transaction_type']}"

        # Verify TP2 order - should use SELL transaction_type for BUY entry
        tp2_call = calls[2]
        assert tp2_call.kwargs['transaction_type'] == 'SELL', \
            f"TP2 order for BUY entry should have transaction_type='SELL', got {tp2_call.kwargs['transaction_type']}"

    @patch('packages.storage.database.order_exists')
    @patch('packages.core.oco.get_db_session')
    def test_on_entry_fill_transaction_type_for_sell_entry(self, mock_db_session, mock_order_exists):
        """Test that on_entry_fill passes correct transaction_type to place_order for SELL entry"""
        # Setup mocks
        mock_order_exists.return_value = False
        mock_db = MagicMock()
        mock_db.__enter__ = Mock(return_value=mock_db)
        mock_db.__exit__ = Mock(return_value=False)
        mock_db_session.return_value = mock_db

        # Mock KiteClient
        kite_client = Mock()
        kite_client.place_order = Mock(return_value="BROKER_ORDER_456")
        oco_manager = OCOManager(kite_client)

        # Create a SELL entry order
        entry_order = Order(
            client_order_id="ENTRY_SELL",
            symbol="NIFTY23OCTFUT",
            instrument_token=12345,
            side=OrderSideEnum.SELL,
            qty=50,
            order_type=OrderTypeEnum.MARKET,
            price=19500.0,
            status=OrderStatusEnum.FILLED,
            strategy_name="TEST_STRAT"
        )

        # Create OCO group
        group_id = oco_manager.create_oco_group(
            entry_order=entry_order,
            stop_price=19600.0,
            tp1_price=19400.0,
            tp2_price=19300.0
        )

        # Call on_entry_fill
        oco_manager.on_entry_fill(group_id)

        # Verify place_order was called 3 times (stop, tp1, tp2)
        assert kite_client.place_order.call_count == 3

        # Get all calls to place_order
        calls = kite_client.place_order.call_args_list

        # Verify Stop Loss order - should use BUY transaction_type for SELL entry
        stop_call = calls[0]
        assert stop_call.kwargs['transaction_type'] == 'BUY', \
            f"Stop order for SELL entry should have transaction_type='BUY', got {stop_call.kwargs['transaction_type']}"

        # Verify TP1 order - should use BUY transaction_type for SELL entry
        tp1_call = calls[1]
        assert tp1_call.kwargs['transaction_type'] == 'BUY', \
            f"TP1 order for SELL entry should have transaction_type='BUY', got {tp1_call.kwargs['transaction_type']}"

        # Verify TP2 order - should use BUY transaction_type for SELL entry
        tp2_call = calls[2]
        assert tp2_call.kwargs['transaction_type'] == 'BUY', \
            f"TP2 order for SELL entry should have transaction_type='BUY', got {tp2_call.kwargs['transaction_type']}"
