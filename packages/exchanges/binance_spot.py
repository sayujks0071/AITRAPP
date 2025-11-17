"""Binance Spot exchange adapter"""
import asyncio
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


class BinanceSpot(Exchange):
    """
    Binance Spot exchange adapter.
    
    Features:
    - REST API with HMAC-SHA256 authentication
    - WebSocket streams (ticker, orderbook, user data)
    - Native OCO support
    - Symbol format: BTCUSDT (no mapping needed)
    - Precision handling (tickSize, stepSize, minNotional)
    """
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: Optional[str] = None,
        testnet: bool = False
    ):
        if base_url is None:
            if testnet:
                base_url = "https://testnet.binance.vision"
            else:
                base_url = "https://api.binance.com"
        
        super().__init__(api_key, api_secret, base_url, testnet)
        
        self.rest_client = httpx.AsyncClient(timeout=30.0)
        self.ws_public: Optional[WebSocketClientProtocol] = None
        self.ws_user: Optional[WebSocketClientProtocol] = None
        self.ws_public_task: Optional[asyncio.Task] = None
        self.ws_user_task: Optional[asyncio.Task] = None
        
        # Binance uses same symbol format (BTCUSDT), no mapping needed
        self._symbol_map: Dict[str, str] = {}
        self._reverse_symbol_map: Dict[str, str] = {}
        
        # OCO tracking (Binance supports native OCO)
        self._oco_groups: Dict[str, List[str]] = {}  # oco_group_id -> [order_ids]
        self._oco_symbols: Dict[str, str] = {}  # oco_group_id -> symbol
        
        # Binance-specific: time sync and rate limits
        self._server_time_offset: float = 0.0  # Offset between local and server time (ms)
        self._listen_key: Optional[str] = None
        self._listen_key_expiry: Optional[float] = None  # Timestamp when listen key expires
        self._used_weight_1m: int = 0
        self._order_count_1m: int = 0
        
        # ExchangeInfo cache with TTL
        self._exchange_info_cache: Optional[Dict[str, Any]] = None
        self._exchange_info_cache_time: float = 0.0
        self._exchange_info_ttl: float = 300.0  # 5 minutes TTL
    
    async def _sync_server_time(self) -> None:
        """Sync server time to calculate offset and update metric"""
        try:
            result = await self._rest_request("GET", "/api/v3/time", {}, private=False)
            server_time = result.get("serverTime", 0)
            local_time = int(time.time() * 1000)
            self._server_time_offset = server_time - local_time
            
            # Update time skew metric
            from packages.core.metrics import binance_time_skew_ms
            binance_time_skew_ms.labels(venue="BINANCE_SPOT").set(abs(self._server_time_offset))
            
            logger.info("Server time synced", offset_ms=self._server_time_offset)
        except Exception as e:
            logger.warning("Failed to sync server time", error=str(e))
            self._server_time_offset = 0.0
    
    def _sign_request(self, params: Dict[str, Any]) -> str:
        """Generate HMAC-SHA256 signature for private API"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_timestamp(self) -> int:
        """Get timestamp adjusted for server time offset"""
        return int((time.time() * 1000) + self._server_time_offset)
    
    async def _rest_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        private: bool = False
    ) -> Dict[str, Any]:
        """Make REST API request with time sync and rate limit monitoring"""
        url = f"{self.base_url}{path}"
        headers = {"X-MBX-APIKEY": self.api_key} if private else {}
        
        if private and params:
            # Use synced timestamp and add recvWindow
            params["timestamp"] = self._get_timestamp()
            params["recvWindow"] = 5000  # 5 second window
            params["signature"] = self._sign_request(params)
        
        if method == "GET":
            if params:
                url += "?" + urlencode(params)
            response = await self.rest_client.get(url, headers=headers)
        elif method == "POST":
            response = await self.rest_client.post(url, headers=headers, params=params)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        # Read rate limit headers and update metrics
        self._used_weight_1m = int(response.headers.get("X-MBX-USED-WEIGHT-1m", "0"))
        self._order_count_1m = int(response.headers.get("X-MBX-ORDER-COUNT-1m", "0"))
        
        # Update Prometheus metrics
        from packages.core.metrics import binance_used_weight_1m, binance_order_count_1m
        binance_used_weight_1m.labels(venue="BINANCE_SPOT").set(self._used_weight_1m)
        binance_order_count_1m.labels(venue="BINANCE_SPOT").set(self._order_count_1m)
        
        response.raise_for_status()
        result = response.json()
        
        # Binance error format
        if "code" in result and result["code"] != 200:
            error_code = result.get("code", 0)
            error_msg = result.get("msg", "Unknown error")
            
            # Handle specific Binance errors
            if error_code == -1021:
                # Timestamp error - resync time
                logger.warning("Timestamp error, resyncing server time")
                await self._sync_server_time()
                raise Exception(f"Binance timestamp error (resynced): {error_msg}")
            elif error_code == -1125:
                # Listen key expired
                logger.warning("Listen key expired")
                await self._renew_listen_key()
                raise Exception(f"Binance listen key expired (renewed): {error_msg}")
            elif error_code in (-2010, -1111):
                # Filter error - invalid price/quantity, refresh exchangeInfo cache
                logger.warning("Filter error, refreshing exchangeInfo cache", error_code=error_code)
                self._exchange_info_cache = None
                self._exchange_info_cache_time = 0.0
                # Reload symbols to refresh cache
                self._symbols_loaded = False
                await self.load_symbols()
                raise Exception(f"Binance filter error (cache refreshed): {error_msg}")
            
            raise Exception(f"Binance API error ({error_code}): {error_msg}")
        
        return result
    
    async def load_symbols(self) -> Dict[str, SymbolInfo]:
        """Load all trading symbols with metadata (cached with TTL)"""
        if self._symbols_loaded:
            return self._symbols
        
        # Check cache first
        if self._exchange_info_cache and (time.time() - self._exchange_info_cache_time) < self._exchange_info_ttl:
            result = self._exchange_info_cache
            logger.debug("Using cached exchangeInfo")
        else:
            # Sync server time before first request
            await self._sync_server_time()
            
            result = await self._rest_request("GET", "/api/v3/exchangeInfo")
            
            # Cache result
            self._exchange_info_cache = result
            self._exchange_info_cache_time = time.time()
            logger.debug("Cached exchangeInfo", ttl_sec=self._exchange_info_ttl)
        
        symbols = {}
        for symbol_data in result.get("symbols", []):
            if symbol_data.get("status") != "TRADING":
                continue
            
            symbol = symbol_data["symbol"]  # e.g., BTCUSDT
            base_asset = symbol_data["baseAsset"]
            quote_asset = symbol_data["quoteAsset"]
            
            # Parse filters
            tick_size = Decimal("0.01")
            step_size = Decimal("0.001")
            min_notional = Decimal("10.0")
            
            # Parse all filters (PRICE_FILTER, LOT_SIZE, MIN_NOTIONAL, PERCENT_PRICE_BY_SIDE)
            for filter_data in symbol_data.get("filters", []):
                filter_type = filter_data.get("filterType")
                if filter_type == "PRICE_FILTER":
                    tick_size = Decimal(str(filter_data.get("tickSize", "0.01")))
                elif filter_type == "LOT_SIZE":
                    step_size = Decimal(str(filter_data.get("stepSize", "0.001")))
                elif filter_type == "MIN_NOTIONAL":
                    min_notional = Decimal(str(filter_data.get("minNotional", "10.0")))
                # PERCENT_PRICE_BY_SIDE is handled implicitly via price rounding
            
            # Calculate precision
            precision_price = len(str(tick_size).split(".")[-1]) if "." in str(tick_size) else 0
            precision_quantity = len(str(step_size).split(".")[-1]) if "." in str(step_size) else 0
            
            symbol_info = SymbolInfo(
                symbol=symbol,
                exchange_symbol=symbol,
                base_asset=base_asset,
                quote_asset=quote_asset,
                tick_size=tick_size,
                step_size=step_size,
                min_notional=min_notional,
                precision_price=precision_price,
                precision_quantity=precision_quantity
            )
            
            symbols[symbol] = symbol_info
            self._symbol_map[symbol] = symbol
            self._reverse_symbol_map[symbol] = symbol
        
        self._symbols = symbols
        self._symbols_loaded = True
        logger.info("Loaded Binance symbols", count=len(symbols))
        return symbols
    
    async def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """Get symbol metadata"""
        if not self._symbols_loaded:
            await self.load_symbols()
        return self._symbols.get(symbol)
    
    async def connect_ws(self) -> None:
        """Connect to WebSocket streams"""
        if self.testnet:
            # Binance testnet uses different WebSocket endpoint
            # Note: Testnet WebSocket may be limited/unavailable
            # For paper mode, we can skip WebSocket if it fails
            ws_url_public = "wss://testnet.binance.vision/stream"
            ws_url_user_base = "wss://testnet.binance.vision/stream"
        else:
            ws_url_public = "wss://stream.binance.com:9443/stream"
            ws_url_user_base = "wss://stream.binance.com:9443/stream"
        
        # Public WebSocket
        try:
            self.ws_public = await websockets.connect(ws_url_public)
            self._ws_connected = True
        except Exception as e:
            logger.warning("Failed to connect to Binance WebSocket (may be unavailable in testnet)", error=str(e))
            if self.testnet:
                # In testnet/paper mode, continue without WebSocket
                logger.info("Continuing in paper mode without WebSocket connection")
                self._ws_connected = False
                return
            raise
        
        # User data stream (private)
        # First, create listen key (requires API key but no signature)
        try:
            await self._create_listen_key()
            if self._listen_key:
                ws_url_user = f"{ws_url_user_base}/{self._listen_key}"
                self.ws_user = await websockets.connect(ws_url_user)
                self.ws_user_task = asyncio.create_task(self._ws_user_handler())
                # Start listen key keepalive task
                asyncio.create_task(self._listen_key_keepalive())
        except Exception as e:
            logger.warning("Failed to create user data stream", error=str(e))
            # Continue without user stream (public data still works)
        
        # Start handlers
        self.ws_public_task = asyncio.create_task(self._ws_public_handler())
        
        # Start periodic time sync (every 5 minutes)
        asyncio.create_task(self._periodic_time_sync())
        
        logger.info("Binance WebSocket connected", user_stream=bool(self.ws_user))
    
    async def disconnect_ws(self) -> None:
        """Disconnect WebSocket streams"""
        if self.ws_public:
            await self.ws_public.close()
            self.ws_public = None
        
        if self.ws_user:
            await self.ws_user.close()
            self.ws_user = None
        
        if self.ws_public_task:
            self.ws_public_task.cancel()
            try:
                await self.ws_public_task
            except asyncio.CancelledError:
                pass
        
        if self.ws_user_task:
            self.ws_user_task.cancel()
            try:
                await self.ws_user_task
            except asyncio.CancelledError:
                pass
        
        self._ws_connected = False
        logger.info("Binance WebSocket disconnected")
    
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
                    
                    # Handle subscription confirmation
                    if "result" in data or "id" in data:
                        continue
                    
                    # Ticker or orderbook update
                    if "e" in data:  # Event type
                        if data["e"] == "24hrTicker":
                            self._emit_ws_message("ticker", data)
                        elif data["e"] == "depthUpdate":
                            # Parse Binance orderbook format
                            orderbook_data = {
                                "bids": [[float(bid[0]), float(bid[1])] for bid in data.get("b", [])],
                                "asks": [[float(ask[0]), float(ask[1])] for ask in data.get("a", [])]
                            }
                            self._emit_ws_message("orderbook", orderbook_data)
                    
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
                jitter = random.uniform(0, base_wait * 0.1)
                wait_time = base_wait + jitter
                logger.info(f"Reconnecting WebSocket in {wait_time:.2f}s (attempt {attempt})")
                await asyncio.sleep(wait_time)
                
                # Reconnect
                try:
                    if self.testnet:
                        ws_url = "wss://testnet.binance.vision/stream"
                    else:
                        ws_url = "wss://stream.binance.com:9443/stream"
                    self.ws_public = await websockets.connect(ws_url)
                    self._ws_connected = True
                    from packages.core.metrics import crypto_ws_reconnects_total
                    crypto_ws_reconnects_total.labels(venue="BINANCE_SPOT").inc()
                    logger.info("WebSocket reconnected")
                except Exception as reconnect_error:
                    logger.error("WebSocket reconnect failed", error=str(reconnect_error))
                    if self.testnet:
                        # In testnet, don't keep retrying aggressively
                        logger.info("Skipping WebSocket in testnet mode")
                        break
    
    async def _ws_user_handler(self) -> None:
        """Handle user data stream messages"""
        try:
            async for message in self.ws_user:
                data = json.loads(message)
                
                # Order update
                if data.get("e") == "executionReport":
                    self._emit_ws_message("execution", data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("User stream handler error", error=str(e))
    
    async def subscribe_ticker(self, symbol: str) -> None:
        """Subscribe to ticker updates"""
        # Binance uses combined stream URL format
        # For now, we'll use the single stream format
        stream_name = f"{symbol.lower()}@ticker"
        subscribe_msg = {
            "method": "SUBSCRIBE",
            "params": [stream_name],
            "id": int(time.time())
        }
        
        if self.ws_public:
            await self.ws_public.send(json.dumps(subscribe_msg))
            logger.info("Subscribed to ticker", symbol=symbol)
    
    async def subscribe_orderbook(self, symbol: str) -> None:
        """Subscribe to orderbook updates"""
        stream_name = f"{symbol.lower()}@depth10@100ms"
        subscribe_msg = {
            "method": "SUBSCRIBE",
            "params": [stream_name],
            "id": int(time.time())
        }
        
        if self.ws_public:
            await self.ws_public.send(json.dumps(subscribe_msg))
            logger.info("Subscribed to orderbook", symbol=symbol)
    
    async def subscribe_orders(self) -> None:
        """Subscribe to private order updates (via user data stream)"""
        # Handled by user data stream
        logger.info("Binance order updates via user data stream")
    
    async def _create_listen_key(self) -> None:
        """Create user data stream listen key"""
        url = f"{self.base_url}/api/v3/userDataStream"
        headers = {"X-MBX-APIKEY": self.api_key}
        response = await self.rest_client.post(url, headers=headers)
        response.raise_for_status()
        listen_key_result = response.json()
        self._listen_key = listen_key_result.get("listenKey")
        # Listen key expires in 60 minutes, renew every 30 minutes
        self._listen_key_expiry = time.time() + 1800  # 30 minutes
        logger.info("Listen key created", expires_in_min=30)
    
    async def _renew_listen_key(self) -> None:
        """Renew user data stream listen key"""
        if not self._listen_key:
            await self._create_listen_key()
            return
        
        url = f"{self.base_url}/api/v3/userDataStream"
        headers = {"X-MBX-APIKEY": self.api_key}
        params = {"listenKey": self._listen_key}
        response = await self.rest_client.put(url, headers=headers, params=params)
        response.raise_for_status()
        # Reset expiry
        self._listen_key_expiry = time.time() + 1800  # 30 minutes
        from packages.core.metrics import binance_listenkey_renew_total
        binance_listenkey_renew_total.labels(venue="BINANCE_SPOT").inc()
        logger.info("Listen key renewed", expires_in_min=30)
    
    async def _listen_key_keepalive(self) -> None:
        """Keepalive task for listen key (renew every 30 minutes)"""
        while True:
            try:
                await asyncio.sleep(1800)  # 30 minutes
                if self._listen_key and self._listen_key_expiry:
                    # Renew if within 5 minutes of expiry
                    if time.time() >= (self._listen_key_expiry - 300):
                        await self._renew_listen_key()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Listen key keepalive error", error=str(e))
                await asyncio.sleep(60)  # Retry in 1 minute
    
    async def _periodic_time_sync(self) -> None:
        """Periodic time sync task (every 5 minutes)"""
        while True:
            try:
                await asyncio.sleep(300)  # 5 minutes
                await self._sync_server_time()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Periodic time sync error", error=str(e))
                await asyncio.sleep(60)  # Retry in 1 minute
    
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
        
        # Build order params
        params = {
            "symbol": symbol,
            "side": "BUY" if side == OrderSide.BUY else "SELL",
            "type": "MARKET" if order_type == OrderType.MARKET else "LIMIT",
            "quantity": str(quantity),
        }
        
        if order_type == OrderType.LIMIT:
            params["timeInForce"] = time_in_force
            if price:
                params["price"] = str(price)
        elif order_type == OrderType.STOP_LOSS:
            params["type"] = "STOP_LOSS_LIMIT"
            if price:
                params["price"] = str(price)
            if stop_price:
                params["stopPrice"] = str(stop_price)
        
        if client_order_id:
            # Ensure idempotency: hash to stable 32-char key
            import hashlib
            stable_id = hashlib.sha256(client_order_id.encode()).hexdigest()[:32]
            params["newClientOrderId"] = stable_id
        else:
            # Generate idempotent client order ID from order params
            import hashlib
            idempotent_key = f"{symbol}_{side.value}_{quantity}_{price if price else 'MARKET'}"
            stable_id = hashlib.sha256(idempotent_key.encode()).hexdigest()[:32]
            params["newClientOrderId"] = stable_id
        
        # Place order
        result = await self._rest_request("POST", "/api/v3/order", params, private=True)
        
        order_id = str(result.get("orderId", "unknown"))
        
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
        params = {}
        if client_order_id:
            params["origClientOrderId"] = client_order_id
        else:
            params["orderId"] = order_id
        
        try:
            await self._rest_request("DELETE", "/api/v3/order", params, private=True)
            logger.info("Order cancelled", order_id=order_id)
            return True
        except Exception as e:
            logger.error("Order cancellation failed", order_id=order_id, error=str(e))
            return False
    
    async def get_order(self, order_id: str, client_order_id: Optional[str] = None) -> Optional[Order]:
        """Get order status"""
        params = {}
        if client_order_id:
            params["origClientOrderId"] = client_order_id
        else:
            params["orderId"] = order_id
        
        try:
            result = await self._rest_request("GET", "/api/v3/order", params, private=True)
            
            # Parse order status
            status_str = result.get("status", "NEW")
            if status_str == "FILLED":
                status = OrderStatus.FILLED
            elif status_str == "CANCELED":
                status = OrderStatus.CANCELLED
            elif status_str == "NEW":
                status = OrderStatus.PENDING
            else:
                status = OrderStatus.OPEN
            
            order = Order(
                order_id=str(result.get("orderId", order_id)),
                client_order_id=result.get("clientOrderId") or order_id,
                symbol=result.get("symbol", ""),
                side=OrderSide.BUY if result.get("side") == "BUY" else OrderSide.SELL,
                order_type=OrderType.MARKET if result.get("type") == "MARKET" else OrderType.LIMIT,
                quantity=Decimal(str(result.get("origQty", "0"))),
                price=Decimal(str(result.get("price", "0"))) if result.get("price") else None,
                status=status,
                filled_quantity=Decimal(str(result.get("executedQty", "0"))),
                average_price=Decimal(str(result.get("price", "0"))) if result.get("executedQty", "0") != "0" else None,
                timestamp=datetime.fromtimestamp(result.get("time", 0) / 1000)
            )
            
            return order
        except Exception as e:
            logger.error("Get order failed", order_id=order_id, error=str(e))
            return None
    
    async def get_positions(self) -> List[Position]:
        """Get all open positions"""
        # Binance spot doesn't have positions (only balances)
        return []
    
    async def get_balances(self) -> Dict[str, Balance]:
        """Get account balances"""
        result = await self._rest_request("GET", "/api/v3/account", {}, private=True)
        
        balances = {}
        for asset_data in result.get("balances", []):
            asset = asset_data["asset"]
            free = Decimal(str(asset_data.get("free", "0")))
            locked = Decimal(str(asset_data.get("locked", "0")))
            total = free + locked
            
            if total > 0:
                balance = Balance(
                    asset=asset,
                    free=free,
                    locked=locked,
                    total=total
                )
                balances[asset] = balance
        
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
    
    def parse_exec_report(self, msg: Dict[str, Any]) -> Optional[ExecutionReport]:
        """Parse execution report from WebSocket message"""
        if msg.get("e") != "executionReport":
            return None
        
        return ExecutionReport(
            order_id=str(msg.get("i", "")),
            client_order_id=msg.get("c", ""),
            symbol=msg.get("s", ""),
            side=OrderSide.BUY if msg.get("S") == "BUY" else OrderSide.SELL,
            quantity=Decimal(str(msg.get("q", "0"))),
            price=Decimal(str(msg.get("p", "0"))),
            filled_quantity=Decimal(str(msg.get("z", "0"))),
            average_price=Decimal(str(msg.get("p", "0"))),
            status=OrderStatus.FILLED if msg.get("X") == "FILLED" else OrderStatus.PENDING,
            timestamp=datetime.fromtimestamp(msg.get("E", 0) / 1000)
        )
    
    def round_quantity(self, quantity: Decimal, symbol_info: SymbolInfo) -> Decimal:
        """Round quantity to step_size"""
        if symbol_info.step_size <= 0:
            return quantity
        return (quantity / symbol_info.step_size).quantize(Decimal("1")) * symbol_info.step_size
    
    def round_price(self, price: Decimal, symbol_info: SymbolInfo) -> Decimal:
        """Round price to tick_size"""
        if symbol_info.tick_size <= 0:
            return price
        return (price / symbol_info.tick_size).quantize(Decimal("1")) * symbol_info.tick_size
    
    def check_min_notional(self, price: Decimal, quantity: Decimal, symbol_info: SymbolInfo) -> bool:
        """Check if order meets minimum notional"""
        notional = price * quantity
        return notional >= symbol_info.min_notional
    
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
        Place OCO order (Binance supports native OCO).
        
        Binance OCO requirements:
        - price: limit price (TP)
        - stopPrice: stop trigger price
        - stopLimitPrice: limit price when stop triggers (can be same as stopPrice)
        - All prices must be rounded to tick_size
        - Quantity must be rounded to step_size
        
        Returns:
            Tuple of (limit_order, stop_order)
        """
        symbol_info = await self.get_symbol_info(symbol)
        if not symbol_info:
            raise ValueError(f"Symbol not found: {symbol}")
        
        # Round prices and quantity BEFORE building params (critical for Binance)
        quantity = self.round_quantity(quantity, symbol_info)
        limit_price = self.round_price(limit_price, symbol_info)
        stop_price = self.round_price(stop_price, symbol_info)
        
        # Check min notional for both orders
        if not self.check_min_notional(limit_price, quantity, symbol_info):
            raise ValueError(f"Limit order notional {limit_price * quantity} < min_notional {symbol_info.min_notional}")
        if not self.check_min_notional(stop_price, quantity, symbol_info):
            raise ValueError(f"Stop order notional {stop_price * quantity} < min_notional {symbol_info.min_notional}")
        
        # Build OCO params (Binance native format)
        params = {
            "symbol": symbol,
            "side": "BUY" if side == OrderSide.BUY else "SELL",
            "quantity": str(quantity),
            "price": str(limit_price),  # TP limit price
            "stopPrice": str(stop_price),  # Stop trigger price
            "stopLimitPrice": str(stop_price),  # Stop limit price (same as stop for simplicity)
            "stopLimitTimeInForce": "GTC"
        }
        
        if client_order_id:
            # Ensure idempotency: hash to stable 32-char key
            import hashlib
            stable_id = hashlib.sha256(client_order_id.encode()).hexdigest()[:32]
            params["listClientOrderId"] = stable_id
        else:
            # Generate idempotent client order ID from OCO params
            import hashlib
            idempotent_key = f"OCO_{symbol}_{side.value}_{quantity}_{limit_price}_{stop_price}"
            stable_id = hashlib.sha256(idempotent_key.encode()).hexdigest()[:32]
            params["listClientOrderId"] = stable_id
        
        # Place OCO order
        result = await self._rest_request("POST", "/api/v3/order/oco", params, private=True)
        
        # Binance returns orderListId and orderReports
        order_list_id = result.get("orderListId")
        order_reports = result.get("orderReports", [])
        
        if len(order_reports) < 2:
            raise ValueError("OCO order did not return 2 orders")
        
        # Find limit and stop orders
        limit_order_data = None
        stop_order_data = None
        for report in order_reports:
            if report.get("type") == "LIMIT":
                limit_order_data = report
            elif "STOP" in report.get("type", ""):
                stop_order_data = report
        
        if not limit_order_data or not stop_order_data:
            raise ValueError("OCO order missing limit or stop order")
        
        # Parse order status (Binance uses NEW, FILLED, PARTIALLY_FILLED, CANCELED)
        limit_status_str = limit_order_data.get("status", "NEW")
        limit_status = OrderStatus.PENDING if limit_status_str == "NEW" else (
            OrderStatus.FILLED if limit_status_str == "FILLED" else OrderStatus.PARTIAL
        )
        
        stop_status_str = stop_order_data.get("status", "NEW")
        stop_status = OrderStatus.PENDING if stop_status_str == "NEW" else (
            OrderStatus.FILLED if stop_status_str == "FILLED" else OrderStatus.PARTIAL
        )
        
        limit_order = Order(
            order_id=str(limit_order_data.get("orderId", "")),
            client_order_id=limit_order_data.get("clientOrderId", ""),
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=limit_price,
            status=limit_status,
            filled_quantity=Decimal(str(limit_order_data.get("executedQty", "0"))),
            timestamp=datetime.now()
        )
        
        stop_order = Order(
            order_id=str(stop_order_data.get("orderId", "")),
            client_order_id=stop_order_data.get("clientOrderId", ""),
            symbol=symbol,
            side=side,
            order_type=OrderType.STOP_LOSS,
            quantity=quantity,
            price=stop_price,
            status=stop_status,
            filled_quantity=Decimal(str(stop_order_data.get("executedQty", "0"))),
            timestamp=datetime.now()
        )
        
        # Track OCO group
        self._oco_groups[str(order_list_id)] = [limit_order.order_id, stop_order.order_id]
        self._oco_symbols[str(order_list_id)] = symbol
        
        logger.info("OCO order placed", order_list_id=order_list_id, symbol=symbol, limit_status=limit_status_str, stop_status=stop_status_str)
        return limit_order, stop_order
    
    async def cancel_oco_group(self, oco_group_id: str) -> None:
        """Cancel OCO group (Binance native)"""
        # Get symbol from tracked OCO groups
        symbol = self._oco_symbols.get(oco_group_id)
        if not symbol:
            # Fallback: cancel individual orders
            order_ids = self._oco_groups.get(oco_group_id, [])
            for order_id in order_ids:
                await self.cancel_order(order_id)
            logger.warning("OCO group cancelled (fallback - no symbol)", oco_group_id=oco_group_id)
            return
        
        params = {
            "symbol": symbol,
            "orderListId": oco_group_id
        }
        
        try:
            await self._rest_request("DELETE", "/api/v3/orderList", params, private=True)
            logger.info("OCO group cancelled", oco_group_id=oco_group_id, symbol=symbol)
        except Exception as e:
            logger.error("OCO group cancellation failed", oco_group_id=oco_group_id, error=str(e))
            # Fallback: cancel individual orders
            order_ids = self._oco_groups.get(oco_group_id, [])
            for order_id in order_ids:
                await self.cancel_order(order_id)

