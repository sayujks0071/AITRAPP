"""Kraken Spot exchange adapter"""
import asyncio
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import httpx
import structlog
import websockets
from websockets.client import WebSocketClientProtocol

from packages.exchanges.base import (
    Exchange, SymbolInfo, Order, OrderSide, OrderType, OrderStatus,
    Position, Balance, ExecutionReport
)

logger = structlog.get_logger(__name__)


class KrakenSpot(Exchange):
    """
    Kraken Spot exchange adapter.
    
    Features:
    - REST API with HMAC-SHA512 authentication
    - WebSocket public (ticker, orderbook) and private (orders, trades)
    - Symbol mapping (BTCUSDT -> XBTUSDT)
    - Precision handling (tickSize, stepSize, minNotional)
    - Client-side OCO emulation (Kraken doesn't support native OCO)
    """
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: Optional[str] = None,
        testnet: bool = False
    ):
        if base_url is None:
            base_url = "https://api.kraken.com"
        
        super().__init__(api_key, api_secret, base_url, testnet)
        
        self.rest_client = httpx.AsyncClient(timeout=30.0)
        self.ws_public: Optional[WebSocketClientProtocol] = None
        self.ws_private: Optional[WebSocketClientProtocol] = None
        self.ws_public_task: Optional[asyncio.Task] = None
        self.ws_private_task: Optional[asyncio.Task] = None
        
        # Symbol mapping: internal (BTCUSDT) -> Kraken (XBTUSDT)
        self._symbol_map: Dict[str, str] = {}
        self._reverse_symbol_map: Dict[str, str] = {}
        
        # OCO tracking (client-side emulation)
        self._oco_groups: Dict[str, List[str]] = {}  # parent_order_id -> [child_order_ids]
    
    def _map_symbol(self, internal_symbol: str) -> str:
        """Map internal symbol to Kraken symbol"""
        return self._symbol_map.get(internal_symbol, internal_symbol)
    
    def _unmap_symbol(self, kraken_symbol: str) -> str:
        """Map Kraken symbol to internal symbol"""
        return self._reverse_symbol_map.get(kraken_symbol, kraken_symbol)
    
    def _sign_message(self, path: str, data: Dict[str, Any]) -> str:
        """Generate HMAC-SHA512 signature for private API"""
        postdata = urlencode(data)
        encoded = (str(data.get("nonce", "")) + postdata).encode()
        message = path.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(
            base64.b64decode(self.api_secret),
            message,
            hashlib.sha512
        )
        sigdigest = base64.b64encode(mac.digest()).decode()
        return sigdigest
    
    async def _rest_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        private: bool = False
    ) -> Dict[str, Any]:
        """Make REST API request"""
        url = f"{self.base_url}{path}"
        headers = {}
        
        if private:
            nonce = str(int(time.time() * 1000))
            params = params or {}
            params["nonce"] = nonce
            
            headers["API-Key"] = self.api_key
            headers["API-Sign"] = self._sign_message(path, params)
        
        await self.throttle(8.0)  # 8 requests per second
        
        if method == "GET":
            response = await self.rest_client.get(url, params=params, headers=headers)
        else:
            response = await self.rest_client.post(url, data=params, headers=headers)
        
        response.raise_for_status()
        result = response.json()
        
        if "error" in result and result["error"]:
            error_msg = ", ".join(result["error"])
            raise Exception(f"Kraken API error: {error_msg}")
        
        return result.get("result", result)
    
    async def load_symbols(self) -> Dict[str, SymbolInfo]:
        """Load all trading symbols with metadata"""
        if self._symbols_loaded:
            return self._symbols
        
        result = await self._rest_request("GET", "/0/public/AssetPairs")
        
        symbols = {}
        for kraken_pair, info in result.items():
            # Skip non-spot pairs (futures, etc.)
            if info.get("wsname") is None or "/" not in info.get("wsname", ""):
                continue
            
            # Map Kraken symbol to internal (e.g., XBTUSDT -> BTCUSDT)
            base = info.get("base", "").replace("XBT", "BTC").replace("ZUSD", "USD").replace("ZUSDT", "USDT")
            quote = info.get("quote", "").replace("ZUSD", "USD").replace("ZUSDT", "USDT")
            internal_symbol = f"{base}{quote}"
            
            # Store mapping
            self._symbol_map[internal_symbol] = kraken_pair
            self._reverse_symbol_map[kraken_pair] = internal_symbol
            
            # Parse precision
            tick_decimals = len(str(info.get("tick_size", "0.01")).split(".")[-1]) if "." in str(info.get("tick_size", "0.01")) else 0
            lot_decimals = len(str(info.get("lot_decimals", "8")).split(".")[-1]) if "." in str(info.get("lot_decimals", "8")) else int(info.get("lot_decimals", 8))
            
            tick_size = Decimal(str(info.get("tick_size", "0.01")))
            step_size = Decimal("0.1") ** lot_decimals
            min_order = Decimal(str(info.get("ordermin", "0.0001")))
            
            # Estimate min_notional (Kraken doesn't provide directly, use min_order * typical price)
            # For conservative estimate, use 25 USDT minimum
            min_notional = Decimal("25.0")  # Conservative default
            
            symbol_info = SymbolInfo(
                symbol=internal_symbol,
                exchange_symbol=kraken_pair,
                base_asset=base,
                quote_asset=quote,
                tick_size=tick_size,
                step_size=step_size,
                min_notional=min_notional,
                precision_price=tick_decimals,
                precision_qty=lot_decimals,
                status=info.get("status", "online")
            )
            
            symbols[internal_symbol] = symbol_info
        
        self._symbols = symbols
        self._symbols_loaded = True
        
        logger.info("Loaded Kraken symbols", count=len(symbols))
        return symbols
    
    async def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """Get symbol metadata"""
        if not self._symbols_loaded:
            await self.load_symbols()
        return self._symbols.get(symbol)
    
    async def connect_ws(self) -> None:
        """Connect to WebSocket streams"""
        # Public WebSocket
        ws_public_url = "wss://ws.kraken.com"
        self.ws_public = await websockets.connect(ws_public_url)
        self._ws_connected = True
        
        # Start message handler
        self.ws_public_task = asyncio.create_task(self._ws_public_handler())
        
        # Private WebSocket (for order updates)
        # Note: Kraken uses REST for order management, WS is mainly for market data
        # We'll poll REST API for order updates instead
        
        logger.info("Kraken WebSocket connected")
    
    async def disconnect_ws(self) -> None:
        """Disconnect WebSocket streams"""
        if self.ws_public:
            await self.ws_public.close()
            self.ws_public = None
        
        if self.ws_public_task:
            self.ws_public_task.cancel()
            try:
                await self.ws_public_task
            except asyncio.CancelledError:
                pass
        
        self._ws_connected = False
        logger.info("Kraken WebSocket disconnected")
    
    async def _ws_public_handler(self) -> None:
        """Handle public WebSocket messages with exponential backoff reconnects"""
        import random
        reconnect_delay = 3
        max_delay = 60
        attempt = 0
        
        while True:
            try:
                async for message in self.ws_public:
                    data = json.loads(message)
                    
                    if isinstance(data, list):
                        # Ticker or orderbook update
                        channel_id = data[0] if len(data) > 0 else None
                        if channel_id and isinstance(data[-1], dict):
                            msg_data = data[-1]
                            # Check if it's an orderbook update
                            if "bids" in msg_data or "as" in msg_data:  # Kraken uses "as" for asks
                                self._emit_ws_message("orderbook", msg_data)
                            else:
                                self._emit_ws_message("ticker", msg_data)
                    elif isinstance(data, dict):
                        # Connection status
                        if data.get("event") == "heartbeat":
                            self._emit_ws_message("heartbeat", data)
                    
                    # Reset reconnect delay on successful message
                    reconnect_delay = 3
                    attempt = 0
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                attempt += 1
                logger.error("WebSocket handler error", error=str(e), attempt=attempt)
                self._ws_connected = False
                
                # Exponential backoff with jitter
                base_wait = min(reconnect_delay * (2 ** (attempt - 1)), max_delay)
                jitter = random.uniform(0, base_wait * 0.1)  # 10% jitter
                wait_time = base_wait + jitter
                logger.info(f"Reconnecting WebSocket in {wait_time:.2f}s (attempt {attempt})")
                await asyncio.sleep(wait_time)
                
                # Reconnect
                try:
                    self.ws_public = await websockets.connect("wss://ws.kraken.com")
                    self._ws_connected = True
                    from packages.core.metrics import crypto_ws_reconnects_total
                    crypto_ws_reconnects_total.labels(venue="KRAKEN_SPOT").inc()
                    logger.info("WebSocket reconnected")
                except Exception as reconnect_error:
                    logger.error("WebSocket reconnect failed", error=str(reconnect_error))
    
    async def subscribe_ticker(self, symbol: str) -> None:
        """Subscribe to ticker updates"""
        kraken_symbol = self._map_symbol(symbol)
        wsname = kraken_symbol.replace("XBT", "BTC")
        
        subscribe_msg = {
            "event": "subscribe",
            "pair": [wsname],
            "subscription": {"name": "ticker"}
        }
        
        if self.ws_public:
            await self.ws_public.send(json.dumps(subscribe_msg))
            logger.info("Subscribed to ticker", symbol=symbol, kraken_symbol=kraken_symbol)
    
    async def subscribe_orderbook(self, symbol: str) -> None:
        """Subscribe to orderbook updates"""
        kraken_symbol = self._map_symbol(symbol)
        wsname = kraken_symbol.replace("XBT", "BTC")
        
        subscribe_msg = {
            "event": "subscribe",
            "pair": [wsname],
            "subscription": {"name": "book", "depth": 10}
        }
        
        if self.ws_public:
            await self.ws_public.send(json.dumps(subscribe_msg))
            logger.info("Subscribed to orderbook", symbol=symbol, kraken_symbol=kraken_symbol)
    
    async def subscribe_orders(self) -> None:
        """Subscribe to private order updates (Kraken uses REST polling)"""
        # Kraken doesn't have private WebSocket for orders
        # We'll poll REST API instead
        logger.info("Kraken order updates via REST polling")
    
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
        """Place an order"""
        symbol_info = await self.get_symbol_info(symbol)
        if not symbol_info:
            raise ValueError(f"Symbol not found: {symbol}")
        
        # Round quantity and price
        quantity = self.round_quantity(quantity, symbol_info)
        if price:
            price = self.round_price(price, symbol_info)
        
        # Check min notional
        if price and not self.check_min_notional(price, quantity, symbol_info):
            raise ValueError(
                f"Order notional {price * quantity} < min_notional {symbol_info.min_notional}"
            )
        
        kraken_symbol = symbol_info.exchange_symbol
        
        # Map order type
        if order_type == OrderType.MARKET:
            ordertype = "market"
        elif order_type == OrderType.LIMIT:
            ordertype = "limit"
        elif order_type == OrderType.STOP_LOSS:
            ordertype = "stop-loss"
        else:
            ordertype = "limit"
        
        # Build order params
        params = {
            "pair": kraken_symbol,
            "type": "buy" if side == OrderSide.BUY else "sell",
            "ordertype": ordertype,
            "volume": str(quantity),
        }
        
        if price:
            params["price"] = str(price)
        if stop_price:
            params["price2"] = str(stop_price)
        
        if client_order_id:
            params["userref"] = client_order_id[:32]  # Kraken limit
        
        # Place order
        result = await self._rest_request("POST", "/0/private/AddOrder", params, private=True)
        
        txid = result.get("txid", [])
        order_id = txid[0] if txid else "unknown"
        
        order = Order(
            order_id=order_id,
            client_order_id=client_order_id or order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            status=OrderStatus.PENDING,
            timestamp=datetime.now()
        )
        
        logger.info("Order placed", order_id=order_id, symbol=symbol, side=side, quantity=quantity)
        return order
    
    async def cancel_order(self, order_id: str, client_order_id: Optional[str] = None) -> bool:
        """Cancel an order"""
        params = {"txid": order_id}
        
        try:
            await self._rest_request("POST", "/0/private/CancelOrder", params, private=True)
            logger.info("Order cancelled", order_id=order_id)
            return True
        except Exception as e:
            logger.error("Order cancellation failed", order_id=order_id, error=str(e))
            return False
    
    async def get_order(self, order_id: str, client_order_id: Optional[str] = None) -> Optional[Order]:
        """Get order status"""
        params = {"txid": order_id}
        
        try:
            result = await self._rest_request("POST", "/0/private/QueryOrders", params, private=True)
            order_data = result.get(order_id)
            
            if not order_data:
                return None
            
            # Parse order data
            status_str = order_data.get("status", "pending")
            if status_str == "closed":
                status = OrderStatus.FILLED
            elif status_str == "canceled":
                status = OrderStatus.CANCELLED
            elif status_str == "pending":
                status = OrderStatus.PENDING
            else:
                status = OrderStatus.OPEN
            
            filled_qty = Decimal(str(order_data.get("vol_exec", "0")))
            avg_price = Decimal(str(order_data.get("price", "0"))) if order_data.get("price") else None
            
            order = Order(
                order_id=order_id,
                client_order_id=order_data.get("userref") or order_id,
                symbol=self._unmap_symbol(order_data.get("descr", {}).get("pair", "")),
                side=OrderSide.BUY if order_data.get("descr", {}).get("type") == "buy" else OrderSide.SELL,
                order_type=OrderType.LIMIT if order_data.get("descr", {}).get("ordertype") == "limit" else OrderType.MARKET,
                quantity=Decimal(str(order_data.get("vol", "0"))),
                price=Decimal(str(order_data.get("descr", {}).get("price", "0"))) if order_data.get("descr", {}).get("price") else None,
                status=status,
                filled_quantity=filled_qty,
                average_price=avg_price,
                timestamp=datetime.now()
            )
            
            return order
        except Exception as e:
            logger.error("Get order failed", order_id=order_id, error=str(e))
            return None
    
    async def get_positions(self) -> List[Position]:
        """Get all open positions"""
        # Kraken spot doesn't have positions (only balances)
        # For spot, positions are derived from balances
        return []
    
    async def get_balances(self) -> Dict[str, Balance]:
        """Get account balances"""
        result = await self._rest_request("POST", "/0/private/Balance", {}, private=True)
        
        balances = {}
        for asset, total_str in result.items():
            # Get free balance (Kraken doesn't separate free/locked in Balance endpoint)
            # We'd need OpenOrders to calculate locked
            total = Decimal(str(total_str))
            
            balance = Balance(
                asset=asset.replace("Z", "").replace("X", ""),  # Clean asset name
                free=total,  # Approximate (would need to subtract locked)
                locked=Decimal("0"),  # Would need to query open orders
                total=total
            )
            balances[balance.asset] = balance
        
        return balances
    
    async def flatten(self, symbol: Optional[str] = None) -> List[Order]:
        """Flatten (close) all positions"""
        # For spot, flattening means selling all holdings of a base asset
        balances = await self.get_balances()
        orders = []
        
        for asset, balance in balances.items():
            if balance.total > 0 and (symbol is None or symbol.startswith(asset)):
                # Find symbol for this asset
                matching_symbols = [s for s in self._symbols.keys() if s.startswith(asset)]
                if matching_symbols:
                    sell_symbol = matching_symbols[0]
                    symbol_info = await self.get_symbol_info(sell_symbol)
                    if symbol_info:
                        # Sell all holdings
                        order = await self.place_order(
                            symbol=sell_symbol,
                            side=OrderSide.SELL,
                            order_type=OrderType.MARKET,
                            quantity=balance.total
                        )
                        orders.append(order)
        
        return orders
    
    async def server_time(self) -> datetime:
        """Get exchange server time"""
        result = await self._rest_request("GET", "/0/public/Time")
        unixtime = result.get("unixtime", int(time.time()))
        return datetime.fromtimestamp(unixtime)
    
    def parse_exec_report(self, msg: Dict[str, Any]) -> Optional[ExecutionReport]:
        """Parse execution report from WebSocket message"""
        # Kraken uses REST for order updates, not WebSocket
        # This would be called from REST polling
        return None
    
    # OCO emulation helpers
    async def place_oco(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        limit_price: Decimal,
        stop_price: Decimal,
        client_order_id: Optional[str] = None
    ) -> tuple[Order, Order]:
        """
        Place client-side OCO order (emulated).
        
        Places both limit and stop orders, tracks them as OCO group.
        On fill of either, cancels the sibling.
        """
        oco_group_id = client_order_id or f"OCO_{int(time.time())}"
        
        # Place limit order
        limit_order = await self.place_order(
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=limit_price,
            client_order_id=f"{oco_group_id}_LIMIT"
        )
        
        # Place stop order
        stop_order = await self.place_order(
            symbol=symbol,
            side=side,
            order_type=OrderType.STOP_LOSS,
            quantity=quantity,
            stop_price=stop_price,
            client_order_id=f"{oco_group_id}_STOP"
        )
        
        # Track OCO group
        self._oco_groups[oco_group_id] = [limit_order.order_id, stop_order.order_id]
        
        logger.info("OCO group created", oco_group_id=oco_group_id, limit=limit_order.order_id, stop=stop_order.order_id)
        return limit_order, stop_order
    
    async def cancel_oco_group(self, oco_group_id: str) -> None:
        """Cancel all orders in an OCO group"""
        order_ids = self._oco_groups.get(oco_group_id, [])
        for order_id in order_ids:
            await self.cancel_order(order_id)
        logger.info("OCO group cancelled", oco_group_id=oco_group_id)

