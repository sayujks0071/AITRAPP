from unittest.mock import Mock, patch
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

        # Assert the expected behavior: if entry is BUY, exit (stop) should be SELL
        assert stop_order.side == OrderSideEnum.SELL, f"Stop order side should be SELL, got {stop_order.side}"

        # Verify TP1 Side
        tp1_order = group.tp1_order
        assert tp1_order.side == OrderSideEnum.SELL, f"TP1 order side should be SELL, got {tp1_order.side}"

        # Verify TP2 Side
        tp2_order = group.tp2_order
        assert tp2_order.side == OrderSideEnum.SELL, f"TP2 order side should be SELL, got {tp2_order.side}"

    def test_child_order_sides_sell_entry(self):
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
            stop_price=19600.0,
            tp1_price=19400.0,
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

    def test_on_entry_fill_uses_correct_transaction_type(self):
        # Mock KiteClient
        kite_client = Mock()
        kite_client.place_order = Mock(return_value="BROKER_ORDER_123")
        oco_manager = OCOManager(kite_client)

        # Create an Entry Order (BUY)
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
            tp1_price=19600.0,
            tp2_price=None
        )

        # Mock database functions
        with patch('packages.core.oco.get_db_session'), \
             patch('packages.storage.database.order_exists', return_value=False):
            # Call on_entry_fill
            oco_manager.on_entry_fill(group_id)

        # Verify that place_order was called with correct transaction_type
        # For BUY entry, stop and TP orders should have SELL transaction_type
        calls = kite_client.place_order.call_args_list
        assert len(calls) == 2  # Stop and TP1

        # Check stop order call
        stop_call = calls[0]
        assert stop_call[1]['transaction_type'] == 'SELL', \
            f"Stop order transaction_type should be SELL, got {stop_call[1]['transaction_type']}"

        # Check TP1 order call
        tp1_call = calls[1]
        assert tp1_call[1]['transaction_type'] == 'SELL', \
            f"TP1 order transaction_type should be SELL, got {tp1_call[1]['transaction_type']}"

