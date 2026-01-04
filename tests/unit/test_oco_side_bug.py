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

        # Verify Stop Order Side (should be SELL)
        stop_order = group.stop_order

        assert stop_order.side == OrderSideEnum.SELL, f"Stop order side should be SELL, got {stop_order.side}"
        # Verify TP1 Side
        tp1_order = group.tp1_order
        assert tp1_order.side == OrderSideEnum.SELL, f"TP1 order side should be SELL, got {tp1_order.side}"

        # Verify TP2 Side
        tp2_order = group.tp2_order
        assert tp2_order.side == OrderSideEnum.SELL, f"TP2 order side should be SELL, got {tp2_order.side}"
    
    def test_child_order_sides_for_sell_entry(self):
        """Test that child orders for SELL entry have BUY side"""
        # Mock KiteClient since OCOManager needs it
        kite_client = Mock()
        oco_manager = OCOManager(kite_client)

        # Create an Entry Order (SHORT/SELL)
        entry_order = Order(
            client_order_id="ENTRY_456",
            symbol="NIFTY23OCTFUT",
            instrument_token=12345,
            side=OrderSideEnum.SELL,
            qty=50,
            order_type=OrderTypeEnum.MARKET,
            price=19500.0,
            status=OrderStatusEnum.FILLED,
            strategy_name="TEST_STRAT"
        )

        # Create OCO group with SL and TP
        group_id = oco_manager.create_oco_group(
            entry_order=entry_order,
            stop_price=19600.0,  # Stop is above for SELL entry
            tp1_price=19400.0,   # TP is below for SELL entry
            tp2_price=19300.0
        )

        group = oco_manager.groups[group_id]

        # Verify Entry Order Side
        assert group.entry_order.side == OrderSideEnum.SELL

        # Verify Stop Order Side (should be BUY)
        stop_order = group.stop_order
        assert stop_order.side == OrderSideEnum.BUY, f"Stop order side should be BUY, got {stop_order.side}"
        
        # Verify TP1 Side
        tp1_order = group.tp1_order
        assert tp1_order.side == OrderSideEnum.BUY, f"TP1 order side should be BUY, got {tp1_order.side}"

        # Verify TP2 Side
        tp2_order = group.tp2_order
        assert tp2_order.side == OrderSideEnum.BUY, f"TP2 order side should be BUY, got {tp2_order.side}"
    
    @patch('packages.core.oco.get_db_session')
    @patch('packages.storage.database.order_exists')
    def test_on_entry_fill_uses_correct_transaction_type(self, mock_order_exists, mock_get_db_session):
        """Test that on_entry_fill passes correct transaction_type to place_order"""
        # Mock database operations
        mock_order_exists.return_value = False  # Orders don't exist yet
        mock_db = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_db
        
        # Mock KiteClient
        kite_client = Mock()
        kite_client.place_order = Mock(return_value="BROKER_ORDER_123")
        
        oco_manager = OCOManager(kite_client)

        # Create a BUY Entry Order
        entry_order = Order(
            client_order_id="ENTRY_789",
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
            tp1_price=19600.0
        )

        # Call on_entry_fill to place child orders
        oco_manager.on_entry_fill(group_id)

        # Verify that place_order was called with correct transaction_type (SELL for BUY entry)
        assert kite_client.place_order.call_count == 2  # Stop and TP1
        
        # Check first call (stop order) - should use SELL
        stop_call = kite_client.place_order.call_args_list[0]
        assert stop_call[1]['transaction_type'] == 'SELL', "Stop order should use SELL transaction_type"
        
        # Check second call (TP1 order) - should use SELL
        tp1_call = kite_client.place_order.call_args_list[1]
        assert tp1_call[1]['transaction_type'] == 'SELL', "TP1 order should use SELL transaction_type"
