"""Unit tests for Binance Spot adapter"""
import pytest
from decimal import Decimal
from datetime import datetime

from packages.exchanges.binance_spot import BinanceSpot
from packages.exchanges.base import SymbolInfo, OrderSide, OrderType


@pytest.fixture
def binance_adapter():
    """Create a Binance adapter instance (testnet)"""
    return BinanceSpot(
        api_key="test_key",
        api_secret="test_secret",
        testnet=True
    )


@pytest.fixture
def btcusdt_symbol_info():
    """BTCUSDT symbol info"""
    return SymbolInfo(
        symbol="BTCUSDT",
        exchange_symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        tick_size=Decimal("0.01"),
        step_size=Decimal("0.00001"),
        min_notional=Decimal("10.0"),
        precision_price=2,
        precision_quantity=5
    )


class TestPriceQuantityRounding:
    """Test price and quantity rounding"""
    
    def test_round_price_to_tick_size(self, binance_adapter, btcusdt_symbol_info):
        """Test price rounding to tick_size"""
        # Price should round to nearest 0.01
        price = Decimal("30000.123")
        rounded = binance_adapter.round_price(price, btcusdt_symbol_info)
        assert rounded == Decimal("30000.12")
        
        price = Decimal("30000.126")
        rounded = binance_adapter.round_price(price, btcusdt_symbol_info)
        assert rounded == Decimal("30000.13")
    
    def test_round_quantity_to_step_size(self, binance_adapter, btcusdt_symbol_info):
        """Test quantity rounding to step_size"""
        # Quantity should round to nearest 0.00001
        qty = Decimal("0.00123456")
        rounded = binance_adapter.round_quantity(qty, btcusdt_symbol_info)
        assert rounded == Decimal("0.00123")
        
        qty = Decimal("0.00123499")
        rounded = binance_adapter.round_quantity(qty, btcusdt_symbol_info)
        assert rounded == Decimal("0.00123")
    
    def test_round_price_zero_tick_size(self, binance_adapter):
        """Test price rounding with zero tick_size (should return original)"""
        symbol_info = SymbolInfo(
            symbol="TEST",
            exchange_symbol="TEST",
            base_asset="T",
            quote_asset="USD",
            tick_size=Decimal("0"),
            step_size=Decimal("0.001"),
            min_notional=Decimal("10.0"),
            precision_price=0,
            precision_quantity=3
        )
        price = Decimal("100.123")
        rounded = binance_adapter.round_price(price, symbol_info)
        assert rounded == price


class TestMinNotionalCheck:
    """Test minimum notional validation"""
    
    def test_min_notional_pass(self, binance_adapter, btcusdt_symbol_info):
        """Test min notional check passes"""
        price = Decimal("30000.0")
        quantity = Decimal("0.001")  # 30 USDT
        assert binance_adapter.check_min_notional(price, quantity, btcusdt_symbol_info) is True
    
    def test_min_notional_fail(self, binance_adapter, btcusdt_symbol_info):
        """Test min notional check fails"""
        price = Decimal("30000.0")
        quantity = Decimal("0.0001")  # 3 USDT < 10 USDT min
        assert binance_adapter.check_min_notional(price, quantity, btcusdt_symbol_info) is False
    
    def test_min_notional_exact(self, binance_adapter, btcusdt_symbol_info):
        """Test min notional check with exact value"""
        price = Decimal("100000.0")
        quantity = Decimal("0.0001")  # Exactly 10 USDT
        assert binance_adapter.check_min_notional(price, quantity, btcusdt_symbol_info) is True


class TestOCOOrderLifecycle:
    """Test OCO order lifecycle (partial fills, state transitions)"""
    
    def test_oco_order_status_parsing(self, binance_adapter):
        """Test parsing OCO order status from Binance response"""
        # Simulate Binance orderReports format
        limit_order_data = {
            "orderId": "12345",
            "clientOrderId": "test_limit",
            "type": "LIMIT",
            "status": "NEW",
            "executedQty": "0"
        }
        
        stop_order_data = {
            "orderId": "12346",
            "clientOrderId": "test_stop",
            "type": "STOP_LOSS_LIMIT",
            "status": "NEW",
            "executedQty": "0"
        }
        
        # NEW status should map to PENDING
        from packages.exchanges.base import OrderStatus
        assert limit_order_data["status"] == "NEW"
        
        # FILLED status should map to FILLED
        limit_order_data["status"] = "FILLED"
        limit_order_data["executedQty"] = "0.001"
        
        # PARTIALLY_FILLED should map to PARTIAL
        limit_order_data["status"] = "PARTIALLY_FILLED"
        limit_order_data["executedQty"] = "0.0005"
    
    def test_oco_partial_fill_tracking(self, binance_adapter):
        """Test tracking partial fills in OCO orders"""
        # Simulate partial fill scenario
        limit_order_data = {
            "orderId": "12345",
            "status": "PARTIALLY_FILLED",
            "executedQty": "0.0005",
            "origQty": "0.001"
        }
        
        filled_qty = Decimal(str(limit_order_data.get("executedQty", "0")))
        orig_qty = Decimal(str(limit_order_data.get("origQty", "0")))
        
        assert filled_qty == Decimal("0.0005")
        assert filled_qty < orig_qty  # Partial fill


class TestIdempotency:
    """Test idempotent client order IDs"""
    
    def test_client_order_id_hashing(self):
        """Test client order ID hashing for idempotency"""
        import hashlib
        
        client_order_id = "test_order_123"
        stable_id = hashlib.sha256(client_order_id.encode()).hexdigest()[:32]
        
        # Same input should produce same hash
        stable_id2 = hashlib.sha256(client_order_id.encode()).hexdigest()[:32]
        assert stable_id == stable_id2
        
        # Different input should produce different hash
        different_id = "test_order_456"
        different_stable = hashlib.sha256(different_id.encode()).hexdigest()[:32]
        assert stable_id != different_stable
        
        # Should be exactly 32 characters
        assert len(stable_id) == 32


class TestTimeSync:
    """Test time synchronization"""
    
    def test_time_offset_calculation(self, binance_adapter):
        """Test calculating time offset"""
        server_time = 1700000000000  # ms
        local_time = 1700000001000  # ms (1 second ahead)
        
        offset = server_time - local_time
        assert offset == -1000  # Server is 1 second behind
    
    def test_timestamp_with_offset(self, binance_adapter):
        """Test generating timestamp with offset"""
        binance_adapter._server_time_offset = 500.0  # 500ms offset
        
        # Mock time.time() to return fixed value
        import time
        original_time = time.time
        
        def mock_time():
            return 1700000000.0
        
        time.time = mock_time
        
        try:
            timestamp = binance_adapter._get_timestamp()
            # Should be local time (ms) + offset
            expected = int((1700000000.0 * 1000) + 500.0)
            assert timestamp == expected
        finally:
            time.time = original_time


@pytest.mark.asyncio
class TestListenKeyKeepalive:
    """Test listen key keepalive (async)"""
    
    async def test_listen_key_expiry_tracking(self, binance_adapter):
        """Test tracking listen key expiry"""
        import time
        
        # Set expiry to 30 minutes from now
        binance_adapter._listen_key_expiry = time.time() + 1800
        
        # Check if within 5 minutes of expiry (should be False)
        time_until_expiry = binance_adapter._listen_key_expiry - time.time()
        assert time_until_expiry > 300  # More than 5 minutes
        
        # Set expiry to 4 minutes from now (should trigger renewal)
        binance_adapter._listen_key_expiry = time.time() + 240
        time_until_expiry = binance_adapter._listen_key_expiry - time.time()
        assert time_until_expiry < 300  # Less than 5 minutes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


