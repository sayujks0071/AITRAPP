"""Crypto venue router - adapts orchestrator to crypto exchanges"""
import asyncio
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any

import structlog

from packages.core.models import (
    Instrument, InstrumentType, Signal, SignalSide, Order, OrderStatus,
    Position, PositionStatus, AssetType, Venue
)
from packages.core.config import AppConfig
from packages.exchanges.base import Exchange, OrderSide as ExchangeOrderSide, OrderType as ExchangeOrderType
from packages.exchanges.kraken_spot import KrakenSpot
from packages.exchanges.binance_spot import BinanceSpot
from packages.core.metrics import (
    crypto_orders_placed_total,
    crypto_ws_reconnects_total,
    oco_orphans_total,
    crypto_flatten_duration_seconds
)

logger = structlog.get_logger(__name__)


class CryptoRouter:
    """
    Router that adapts AITRAPP orchestrator to crypto exchanges.
    
    Responsibilities:
    - Map AITRAPP orders/signals to exchange API
    - Handle symbol mapping (BTCUSDT <-> exchange format)
    - Enforce precision and minNotional
    - Emulate OCO if native OCO not supported
    - Publish Prometheus metrics
    """
    
    def __init__(
        self,
        exchange: Exchange,
        config: AppConfig,
        venue: Venue = Venue.KRAKEN_SPOT,
        paper_mode: bool = False
    ):
        self.exchange = exchange
        self.config = config
        self.venue = venue
        self.paper_mode = paper_mode
        
        # Symbol cache
        self._instruments: Dict[str, Instrument] = {}
        
        # OCO tracking
        self._oco_groups: Dict[str, List[str]] = {}  # parent_order_id -> [child_order_ids]
        
        # Paper mode tracking
        self._paper_orders: Dict[str, Order] = {}
        self._paper_positions: Dict[str, Position] = {}
        self._paper_order_counter = 0
        
        # Orderbook cache for spread guard
        self._orderbook_cache: Dict[str, Dict[str, Decimal]] = {}  # symbol -> {bid, ask, timestamp}
    
    async def initialize(self) -> None:
        """Initialize router and load symbols"""
        await self.exchange.load_symbols()
        await self._build_instruments()
        logger.info("Crypto router initialized", venue=self.venue.value)
    
    async def _build_instruments(self) -> None:
        """Build Instrument objects from exchange symbols"""
        symbols = await self.exchange.load_symbols()
        
        for symbol, symbol_info in symbols.items():
            # Generate a token ID (hash of symbol for consistency)
            token = hash(symbol) % (2**31)  # Keep in int32 range
            
            instrument = Instrument(
                token=token,
                symbol=symbol,
                tradingsymbol=symbol,
                exchange=self.venue.value,
                instrument_type=InstrumentType.CRYPTO,
                lot_size=1,  # Crypto doesn't use lot sizes
                tick_size=float(symbol_info.tick_size),
                venue=self.venue,
                asset_type=AssetType.CRYPTO
            )
            
            self._instruments[symbol] = instrument
        
        logger.info("Built instruments", count=len(self._instruments))
    
    def get_instrument(self, symbol: str) -> Optional[Instrument]:
        """Get instrument by symbol"""
        return self._instruments.get(symbol)
    
    async def connect_ws(self) -> None:
        """Connect to exchange WebSocket"""
        await self.exchange.connect_ws()
        logger.info("Crypto WebSocket connected", venue=self.venue.value)
    
    async def subscribe_symbol(self, symbol: str) -> None:
        """Subscribe to market data for a symbol"""
        await self.exchange.subscribe_ticker(symbol)
        await self.exchange.subscribe_orderbook(symbol)
        
        # Register callback for orderbook updates
        def on_orderbook_update(data: Dict[str, Any]) -> None:
            """Handle orderbook update and cache best bid/ask"""
            if isinstance(data, dict) and "bids" in data and "asks" in data:
                bids = data.get("bids", [])
                asks = data.get("asks", [])
                
                if bids and asks:
                    # Get best bid (highest) and best ask (lowest)
                    best_bid = Decimal(str(bids[0][0])) if bids[0] else None
                    best_ask = Decimal(str(asks[0][0])) if asks[0] else None
                    
                    if best_bid and best_ask:
                        self._orderbook_cache[symbol] = {
                            "bid": best_bid,
                            "ask": best_ask,
                            "timestamp": datetime.now()
                        }
        
        self.exchange.on_ws_message("orderbook", on_orderbook_update)
        logger.info("Subscribed to symbol", symbol=symbol, venue=self.venue.value)
    
    async def place_order_from_signal(
        self,
        signal: Signal,
        quantity: Decimal
    ) -> Optional[Order]:
        """
        Place order from AITRAPP signal.
        
        Args:
            signal: Trading signal
            quantity: Position size (already risk-checked)
        
        Returns:
            AITRAPP Order object
        """
        symbol_info = await self.exchange.get_symbol_info(signal.instrument.symbol)
        if not symbol_info:
            logger.error("Symbol not found", symbol=signal.instrument.symbol)
            return None
        
        # Round quantity and price
        quantity = self.exchange.round_quantity(quantity, symbol_info)
        entry_price = Decimal(str(signal.entry_price))
        entry_price = self.exchange.round_price(entry_price, symbol_info)
        
        # Check min notional
        if not self.exchange.check_min_notional(entry_price, quantity, symbol_info):
            logger.error(
                "Order below min notional",
                symbol=signal.instrument.symbol,
                notional=float(entry_price * quantity),
                min_notional=float(symbol_info.min_notional)
            )
            return None
        
        # Map signal side to exchange side
        exchange_side = ExchangeOrderSide.BUY if signal.side == SignalSide.LONG else ExchangeOrderSide.SELL
        
        # Generate client order ID
        client_order_id = f"{signal.strategy_name}_{signal.instrument.symbol}_{int(signal.timestamp.timestamp())}"
        
        # Check spread guard (50 bps max)
        spread_ok = await self._check_spread_guard(signal.instrument.symbol, entry_price)
        if not spread_ok:
            logger.warning("Spread guard failed", symbol=signal.instrument.symbol)
            return None
        
        # Paper mode: simulate order
        if self.paper_mode:
            exchange_order = await self._simulate_order(
                symbol=signal.instrument.symbol,
                side=exchange_side,
                order_type=ExchangeOrderType.LIMIT,
                quantity=quantity,
                price=entry_price,
                client_order_id=client_order_id
            )
        else:
            # Place entry order
            exchange_order = await self.exchange.place_order(
                symbol=signal.instrument.symbol,
                side=exchange_side,
                order_type=ExchangeOrderType.LIMIT,
                quantity=quantity,
                price=entry_price,
                client_order_id=client_order_id
            )
        
        # Convert to AITRAPP Order
        order = Order(
            order_id=exchange_order.order_id,
            client_order_id=exchange_order.client_order_id,
            timestamp=datetime.now(),
            instrument=signal.instrument,
            side="BUY" if signal.side == SignalSide.LONG else "SELL",
            quantity=int(quantity),
            price=float(entry_price),
            order_type="LIMIT",
            product="SPOT",  # Spot trading
            status=OrderStatus.PENDING,
            strategy_name=signal.strategy_name
        )
        
        # Record metrics
        crypto_orders_placed_total.labels(
            venue=self.venue.value,
            symbol=signal.instrument.symbol,
            side=order.side
        ).inc()
        
        logger.info(
            "Order placed via crypto router",
            order_id=order.order_id,
            symbol=signal.instrument.symbol,
            side=order.side,
            quantity=quantity
        )
        
        return order
    
    async def place_oco(
        self,
        symbol: str,
        side: SignalSide,
        quantity: Decimal,
        limit_price: Decimal,
        stop_price: Decimal,
        client_order_id: Optional[str] = None
    ) -> tuple[Optional[Order], Optional[Order]]:
        """
        Place OCO order (uses native OCO if supported, otherwise client-side emulation).
        
        Returns:
            (limit_order, stop_order) tuple
        """
        from packages.exchanges.binance_spot import BinanceSpot
        
        exchange_side = ExchangeOrderSide.BUY if side == SignalSide.LONG else ExchangeOrderSide.SELL
        
        # Binance supports native OCO
        if isinstance(self.exchange, BinanceSpot):
            limit_ex_order, stop_ex_order = await self.exchange.place_oco(
                symbol=symbol,
                side=exchange_side,
                quantity=quantity,
                limit_price=limit_price,
                stop_price=stop_price,
                client_order_id=client_order_id
            )
        # Kraken: client-side emulation
        elif isinstance(self.exchange, KrakenSpot):
            limit_ex_order, stop_ex_order = await self.exchange.place_oco(
                symbol=symbol,
                side=exchange_side,
                quantity=quantity,
                limit_price=limit_price,
                stop_price=stop_price,
                client_order_id=client_order_id
            )
        else:
            logger.warning("OCO not implemented for this exchange")
            return None, None
        
        # Convert to AITRAPP Orders
        instrument = self.get_instrument(symbol)
        if not instrument:
            logger.error("Instrument not found for OCO", symbol=symbol)
            return None, None
        
        limit_order = Order(
            order_id=limit_ex_order.order_id,
            client_order_id=limit_ex_order.client_order_id,
            timestamp=datetime.now(),
            instrument=instrument,
            side="BUY" if side == SignalSide.LONG else "SELL",
            quantity=int(quantity),
            price=float(limit_price),
            order_type="LIMIT",
            product="SPOT",
            status=OrderStatus.PENDING,
            is_take_profit=True
        )
        
        stop_order = Order(
            order_id=stop_ex_order.order_id,
            client_order_id=stop_ex_order.client_order_id,
            timestamp=datetime.now(),
            instrument=instrument,
            side="SELL" if side == SignalSide.LONG else "BUY",
            quantity=int(quantity),
            price=float(stop_price),
            order_type="SL",
            product="SPOT",
            status=OrderStatus.PENDING,
            is_stop_loss=True
        )
        
        # Track OCO group
        oco_group_id = client_order_id or f"OCO_{limit_order.order_id}"
        self._oco_groups[oco_group_id] = [limit_order.order_id, stop_order.order_id]
        
        logger.info("OCO order placed", symbol=symbol, client_order_id=client_order_id, native=isinstance(self.exchange, BinanceSpot))
        return limit_order, stop_order
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        if self.paper_mode:
            # In paper mode, mark order as cancelled
            order = self._paper_orders.get(order_id)
            if order:
                from packages.exchanges.base import OrderStatus as ExchangeOrderStatus
                order.status = ExchangeOrderStatus.CANCELLED
                logger.info("Order cancelled (paper)", order_id=order_id, venue=self.venue.value)
                return True
            return False
        
        # Live mode: use exchange
        success = await self.exchange.cancel_order(order_id)
        if success:
            logger.info("Order cancelled", order_id=order_id, venue=self.venue.value)
        return success
    
    async def cancel_oco_group(self, oco_group_id: str) -> None:
        """Cancel all orders in an OCO group"""
        from packages.exchanges.binance_spot import BinanceSpot
        from packages.exchanges.kraken_spot import KrakenSpot
        
        if self.paper_mode:
            # In paper mode, mark orders as cancelled
            order_ids = self._oco_groups.get(oco_group_id, [])
            for order_id in order_ids:
                order = self._paper_orders.get(order_id)
                if order:
                    from packages.exchanges.base import OrderStatus as ExchangeOrderStatus
                    order.status = ExchangeOrderStatus.CANCELLED
            logger.info("OCO group cancelled (paper)", oco_group_id=oco_group_id)
        elif isinstance(self.exchange, BinanceSpot):
            # Binance native OCO cancellation
            await self.exchange.cancel_oco_group(oco_group_id)
            logger.info("OCO group cancelled (native)", oco_group_id=oco_group_id)
        elif isinstance(self.exchange, KrakenSpot):
            # Kraken: cancel individual orders
            order_ids = self._oco_groups.get(oco_group_id, [])
            for order_id in order_ids:
                await self.cancel_order(order_id)
            logger.info("OCO group cancelled (emulated)", oco_group_id=oco_group_id)
        else:
            order_ids = self._oco_groups.get(oco_group_id, [])
            for order_id in order_ids:
                await self.cancel_order(order_id)
            logger.info("OCO group cancelled", oco_group_id=oco_group_id)
    
    async def flatten(self, symbol: Optional[str] = None) -> List[Order]:
        """
        Flatten (close) all positions or positions for a symbol.
        
        Returns:
            List of closing orders
        """
        if self.paper_mode:
            # In paper mode, just cancel all OCO groups and clear positions
            for oco_group_id in list(self._oco_groups.keys()):
                await self.cancel_oco_group(oco_group_id)
            
            # Clear paper positions
            self._paper_positions.clear()
            logger.info("Flattened paper positions", symbol=symbol)
            return []
        
        # Live mode: use exchange
        exchange_orders = await self.exchange.flatten(symbol)
        
        orders = []
        for ex_order in exchange_orders:
            instrument = self.get_instrument(ex_order.symbol)
            if instrument:
                order = Order(
                    order_id=ex_order.order_id,
                    client_order_id=ex_order.client_order_id,
                    timestamp=datetime.now(),
                    instrument=instrument,
                    side=ex_order.side.value,
                    quantity=int(ex_order.quantity),
                    price=float(ex_order.price) if ex_order.price else 0.0,
                    order_type=ex_order.order_type.value,
                    product="SPOT",
                    status=OrderStatus.PENDING
                )
                orders.append(order)
        
        logger.info("Flattened positions", symbol=symbol, orders=len(orders))
        return orders
    
    async def get_positions(self) -> List[Position]:
        """Get all open positions"""
        # For spot, positions are derived from balances
        # This is a simplified version - in production, track positions from fills
        return []
    
    async def get_balances(self) -> Dict[str, Decimal]:
        """Get account balances"""
        balances = await self.exchange.get_balances()
        return {asset: balance.total for asset, balance in balances.items()}
    
    async def check_oco_orphans(self) -> None:
        """
        Check for OCO orphan orders (one filled, sibling not cancelled).
        
        This should be called periodically to ensure OCO invariants.
        """
        for oco_group_id, order_ids in self._oco_groups.items():
            filled_count = 0
            for order_id in order_ids:
                if self.paper_mode:
                    order = self._paper_orders.get(order_id)
                    # Check if order is filled (ExchangeOrder has is_filled property)
                    if order and hasattr(order, 'is_filled') and order.is_filled:
                        filled_count += 1
                else:
                    order = await self.exchange.get_order(order_id)
                    if order and order.is_filled:
                        filled_count += 1
            
            # If one is filled, cancel the other
            if filled_count == 1:
                for order_id in order_ids:
                    if self.paper_mode:
                        order = self._paper_orders.get(order_id)
                        if order and hasattr(order, 'is_active') and order.is_active:
                            from packages.exchanges.base import OrderStatus as ExchangeOrderStatus
                            order.status = ExchangeOrderStatus.CANCELLED
                            oco_orphans_total.labels(venue=self.venue.value).inc()
                            logger.warning("Cancelled OCO orphan (paper)", oco_group_id=oco_group_id, order_id=order_id)
                    else:
                        order = await self.exchange.get_order(order_id)
                        if order and order.is_active:
                            await self.cancel_order(order_id)
                            oco_orphans_total.labels(venue=self.venue.value).inc()
                            logger.warning("Cancelled OCO orphan", oco_group_id=oco_group_id, order_id=order_id)
    
    async def _check_spread_guard(self, symbol: str, price: Decimal) -> bool:
        """
        Check spread guard: reject if (ask/bid - 1) > 0.50% (50 bps).
        
        Returns:
            True if spread is acceptable, False otherwise
        """
        orderbook = self._orderbook_cache.get(symbol)
        
        # If no orderbook data, allow (will be checked when data arrives)
        if not orderbook:
            logger.debug("No orderbook data for spread check", symbol=symbol)
            return True
        
        # Check if orderbook data is stale (> 5 seconds)
        age = (datetime.now() - orderbook["timestamp"]).total_seconds()
        if age > 5.0:
            logger.warning("Orderbook data stale", symbol=symbol, age_sec=age)
            return True  # Allow if stale (better than blocking)
        
        bid = orderbook.get("bid")
        ask = orderbook.get("ask")
        
        if not bid or not ask or bid <= 0 or ask <= 0:
            return True
        
        # Calculate spread percentage
        spread_pct = float((ask - bid) / bid) * 100
        spread_bps = spread_pct * 100  # Convert to basis points
        
        if spread_bps > 50:  # 50 bps = 0.50%
            logger.warning(
                "Spread guard failed",
                symbol=symbol,
                spread_bps=spread_bps,
                bid=float(bid),
                ask=float(ask)
            )
            return False
        
        logger.debug(
            "Spread guard passed",
            symbol=symbol,
            spread_bps=spread_bps,
            bid=float(bid),
            ask=float(ask)
        )
        return True
    
    async def _simulate_order(
        self,
        symbol: str,
        side: ExchangeOrderSide,
        order_type: ExchangeOrderType,
        quantity: Decimal,
        price: Decimal,
        client_order_id: str
    ) -> Any:
        """Simulate order in paper mode (instant fill at mid ± slippage)"""
        from packages.exchanges.base import Order as ExchangeOrder, OrderStatus as ExchangeOrderStatus
        
        self._paper_order_counter += 1
        order_id = f"PAPER_CRYPTO_{self._paper_order_counter:08d}"
        
        # Simulate slippage (5 bps)
        slippage_bps = 5
        slippage_mult = Decimal(str(slippage_bps)) / Decimal("10000")
        
        if side == ExchangeOrderSide.BUY:
            fill_price = price * (Decimal("1") + slippage_mult)
        else:
            fill_price = price * (Decimal("1") - slippage_mult)
        
        # Create simulated exchange order
        exchange_order = ExchangeOrder(
            order_id=order_id,
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status=ExchangeOrderStatus.FILLED,
            filled_quantity=quantity,
            average_price=fill_price,
            timestamp=datetime.now()
        )
        
        # Store for tracking
        self._paper_orders[order_id] = exchange_order
        
        logger.info(
            "[PAPER] Crypto order simulated",
            order_id=order_id,
            symbol=symbol,
            side=side.value,
            quantity=quantity,
            fill_price=float(fill_price)
        )
        
        return exchange_order
    
    async def simulate_plan(
        self,
        plan: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Simulate a trading plan in paper mode.
        
        Args:
            plan: Dict with symbol, side, qty, type, stop_pct, tp_pct, client_plan_id
        
        Returns:
            (success: bool, plan_id: str)
        """
        if not self.paper_mode:
            logger.error("simulate_plan only works in paper mode")
            return False, None
        
        symbol = plan.get("symbol")
        side_str = plan.get("side", "LONG")
        qty = Decimal(str(plan.get("qty", 0)))
        order_type_str = plan.get("type", "MARKET")
        stop_pct = plan.get("stop_pct", 0.005)
        tp_pct = plan.get("tp_pct", 0.010)
        import time
        client_plan_id = plan.get("client_plan_id", f"plan_{int(time.time())}")
        
        # Get instrument
        instrument = self.get_instrument(symbol)
        if not instrument:
            logger.error("Instrument not found", symbol=symbol)
            return False, None
        
        # Get symbol info for price
        symbol_info = await self.exchange.get_symbol_info(symbol)
        if not symbol_info:
            logger.error("Symbol info not found", symbol=symbol)
            return False, None
        
        # Get current price (simulated - would use real market data)
        # For now, use a placeholder price
        current_price = Decimal("50000")  # Placeholder for BTCUSDT
        
        # Calculate entry, stop, and TP prices
        entry_price = current_price
        if side_str == "LONG":
            stop_price = entry_price * (Decimal("1") - Decimal(str(stop_pct)))
            tp_price = entry_price * (Decimal("1") + Decimal(str(tp_pct)))
        else:
            stop_price = entry_price * (Decimal("1") + Decimal(str(stop_pct)))
            tp_price = entry_price * (Decimal("1") - Decimal(str(tp_pct)))
        
        # Round prices
        entry_price = self.exchange.round_price(entry_price, symbol_info)
        stop_price = self.exchange.round_price(stop_price, symbol_info)
        tp_price = self.exchange.round_price(tp_price, symbol_info)
        qty = self.exchange.round_quantity(qty, symbol_info)
        
        # Check min notional
        if not self.exchange.check_min_notional(entry_price, qty, symbol_info):
            logger.error("Order below min notional", notional=float(entry_price * qty))
            return False, None
        
        # Map side
        side = SignalSide.LONG if side_str == "LONG" else SignalSide.SHORT
        exchange_side = ExchangeOrderSide.BUY if side == SignalSide.LONG else ExchangeOrderSide.SELL
        
        # Simulate entry order
        entry_order = await self._simulate_order(
            symbol=symbol,
            side=exchange_side,
            order_type=ExchangeOrderType.MARKET if order_type_str == "MARKET" else ExchangeOrderType.LIMIT,
            quantity=qty,
            price=entry_price,
            client_order_id=f"{client_plan_id}_ENTRY"
        )
        
        # Simulate OCO (stop + TP)
        stop_order = await self._simulate_order(
            symbol=symbol,
            side=ExchangeOrderSide.SELL if side == SignalSide.LONG else ExchangeOrderSide.BUY,
            order_type=ExchangeOrderType.STOP_LOSS,
            quantity=qty,
            price=stop_price,
            client_order_id=f"{client_plan_id}_STOP"
        )
        
        tp_order = await self._simulate_order(
            symbol=symbol,
            side=ExchangeOrderSide.SELL if side == SignalSide.LONG else ExchangeOrderSide.BUY,
            order_type=ExchangeOrderType.LIMIT,
            quantity=qty,
            price=tp_price,
            client_order_id=f"{client_plan_id}_TP"
        )
        
        # Track OCO group
        self._oco_groups[client_plan_id] = [stop_order.order_id, tp_order.order_id]
        
        logger.info(
            "Plan simulated",
            plan_id=client_plan_id,
            symbol=symbol,
            entry=entry_order.order_id,
            stop=stop_order.order_id,
            tp=tp_order.order_id
        )
        
        return True, client_plan_id

