"""Base exchange adapter interface for crypto exchanges"""
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class OrderSide(str, Enum):
    """Order side"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"


class OrderStatus(str, Enum):
    """Order status"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class SymbolInfo:
    """Symbol metadata"""
    symbol: str  # Internal symbol (e.g., BTCUSDT)
    exchange_symbol: str  # Exchange-specific symbol (e.g., XBTUSDT on Kraken)
    base_asset: str  # Base asset (e.g., BTC)
    quote_asset: str  # Quote asset (e.g., USDT)
    tick_size: Decimal  # Minimum price increment
    step_size: Decimal  # Minimum quantity increment
    min_notional: Decimal  # Minimum order value in quote currency
    precision_price: int  # Decimal places for price
    precision_qty: int  # Decimal places for quantity
    status: str = "TRADING"  # TRADING, HALTED, etc.


@dataclass
class Order:
    """Exchange order representation"""
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal("0")
    average_price: Optional[Decimal] = None
    timestamp: datetime = None
    exchange_timestamp: Optional[datetime] = None
    
    # OCO metadata
    oco_group_id: Optional[str] = None
    is_stop_loss: bool = False
    is_take_profit: bool = False
    
    @property
    def is_active(self) -> bool:
        """Check if order is still active"""
        return self.status in (OrderStatus.PENDING, OrderStatus.OPEN, OrderStatus.PARTIAL)
    
    @property
    def is_filled(self) -> bool:
        """Check if order is fully filled"""
        return self.status == OrderStatus.FILLED
    
    @property
    def remaining_quantity(self) -> Decimal:
        """Remaining quantity to fill"""
        return self.quantity - self.filled_quantity


@dataclass
class Position:
    """Position representation"""
    symbol: str
    side: OrderSide
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    
    @property
    def notional(self) -> Decimal:
        """Current position notional value"""
        return self.quantity * self.current_price


@dataclass
class Balance:
    """Account balance"""
    asset: str
    free: Decimal  # Available balance
    locked: Decimal  # Locked in orders
    total: Decimal  # Total balance
    
    @property
    def available(self) -> Decimal:
        """Available balance (alias for free)"""
        return self.free


@dataclass
class ExecutionReport:
    """Order execution report"""
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    status: OrderStatus
    filled_quantity: Decimal
    average_price: Optional[Decimal]
    timestamp: datetime
    exchange_timestamp: Optional[datetime] = None
    reject_reason: Optional[str] = None


class Exchange(ABC):
    """
    Abstract base class for crypto exchange adapters.
    
    Provides unified interface for:
    - Symbol metadata and precision handling
    - Order placement and management
    - WebSocket market data and order updates
    - Position and balance queries
    - OCO order emulation (if native OCO not supported)
    """
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: Optional[str] = None,
        testnet: bool = False
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.testnet = testnet
        
        # Symbol cache
        self._symbols: Dict[str, SymbolInfo] = {}
        self._symbols_loaded = False
        
        # WebSocket state
        self._ws_connected = False
        self._ws_reconnect_delay = 3
        self._ws_callbacks: Dict[str, List[Callable]] = {}
        
        # Rate limiting
        self._rate_limiter: Optional[asyncio.Semaphore] = None
        self._last_request_time: float = 0.0
    
    @abstractmethod
    async def load_symbols(self) -> Dict[str, SymbolInfo]:
        """
        Load and cache all trading symbols with metadata.
        
        Returns:
            Dict mapping internal symbol (e.g., BTCUSDT) to SymbolInfo
        """
        pass
    
    @abstractmethod
    async def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """
        Get symbol metadata.
        
        Args:
            symbol: Internal symbol (e.g., BTCUSDT)
        
        Returns:
            SymbolInfo or None if not found
        """
        pass
    
    @abstractmethod
    async def connect_ws(self) -> None:
        """Connect to WebSocket streams (public + private)"""
        pass
    
    @abstractmethod
    async def disconnect_ws(self) -> None:
        """Disconnect WebSocket streams"""
        pass
    
    @abstractmethod
    async def subscribe_ticker(self, symbol: str) -> None:
        """Subscribe to ticker updates for a symbol"""
        pass
    
    @abstractmethod
    async def subscribe_orderbook(self, symbol: str) -> None:
        """Subscribe to orderbook updates for a symbol"""
        pass
    
    @abstractmethod
    async def subscribe_orders(self) -> None:
        """Subscribe to private order updates"""
        pass
    
    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        client_order_id: Optional[str] = None,
        time_in_force: str = "GTC"
    ) -> Order:
        """
        Place an order.
        
        Args:
            symbol: Internal symbol (e.g., BTCUSDT)
            side: BUY or SELL
            order_type: MARKET, LIMIT, STOP_LOSS, etc.
            quantity: Order quantity (will be rounded to step_size)
            price: Limit price (required for LIMIT orders)
            stop_price: Stop price (required for STOP_LOSS orders)
            client_order_id: Idempotent client order ID
            time_in_force: GTC, IOC, FOK (default: GTC)
        
        Returns:
            Order object
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, client_order_id: Optional[str] = None) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Exchange order ID
            client_order_id: Client order ID (alternative lookup)
        
        Returns:
            True if cancelled successfully
        """
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str, client_order_id: Optional[str] = None) -> Optional[Order]:
        """
        Get order status.
        
        Args:
            order_id: Exchange order ID
            client_order_id: Client order ID (alternative lookup)
        
        Returns:
            Order or None if not found
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get all open positions"""
        pass
    
    @abstractmethod
    async def get_balances(self) -> Dict[str, Balance]:
        """
        Get account balances.
        
        Returns:
            Dict mapping asset (e.g., USDT) to Balance
        """
        pass
    
    @abstractmethod
    async def flatten(self, symbol: Optional[str] = None) -> List[Order]:
        """
        Flatten (close) all positions or positions for a specific symbol.
        
        Args:
            symbol: Optional symbol to flatten (None = all positions)
        
        Returns:
            List of closing orders
        """
        pass
    
    @abstractmethod
    async def server_time(self) -> datetime:
        """Get exchange server time"""
        pass
    
    @abstractmethod
    def parse_exec_report(self, msg: Dict[str, Any]) -> Optional[ExecutionReport]:
        """
        Parse execution report from WebSocket message.
        
        Args:
            msg: WebSocket message dict
        
        Returns:
            ExecutionReport or None if not an execution report
        """
        pass
    
    # Precision helpers
    def round_price(self, price: Decimal, symbol_info: SymbolInfo) -> Decimal:
        """Round price to tick_size"""
        if symbol_info.tick_size == 0:
            return price
        ticks = (price / symbol_info.tick_size).quantize(Decimal("1"), rounding="ROUND_DOWN")
        return ticks * symbol_info.tick_size
    
    def round_quantity(self, quantity: Decimal, symbol_info: SymbolInfo) -> Decimal:
        """Round quantity to step_size"""
        if symbol_info.step_size == 0:
            return quantity
        steps = (quantity / symbol_info.step_size).quantize(Decimal("1"), rounding="ROUND_DOWN")
        return steps * symbol_info.step_size
    
    def check_min_notional(
        self,
        price: Decimal,
        quantity: Decimal,
        symbol_info: SymbolInfo
    ) -> bool:
        """
        Check if order meets minimum notional requirement.
        
        Args:
            price: Order price
            quantity: Order quantity
            symbol_info: Symbol metadata
        
        Returns:
            True if notional >= min_notional
        """
        notional = price * quantity
        return notional >= symbol_info.min_notional
    
    # Rate limiting
    async def throttle(self, requests_per_second: float) -> None:
        """
        Throttle requests to respect rate limits.
        
        Args:
            requests_per_second: Max requests per second
        """
        if requests_per_second <= 0:
            return
        
        now = asyncio.get_event_loop().time()
        min_interval = 1.0 / requests_per_second
        elapsed = now - self._last_request_time
        
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        
        self._last_request_time = asyncio.get_event_loop().time()
    
    # WebSocket callbacks
    def on_ws_message(self, msg_type: str, callback: Callable) -> None:
        """Register callback for WebSocket message type"""
        if msg_type not in self._ws_callbacks:
            self._ws_callbacks[msg_type] = []
        self._ws_callbacks[msg_type].append(callback)
    
    def _emit_ws_message(self, msg_type: str, data: Any) -> None:
        """Emit WebSocket message to registered callbacks"""
        callbacks = self._ws_callbacks.get(msg_type, [])
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error("WebSocket callback error", msg_type=msg_type, error=str(e))
    
    @property
    def is_ws_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self._ws_connected


