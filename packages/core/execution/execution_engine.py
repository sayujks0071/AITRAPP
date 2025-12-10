import asyncio
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
import logging
import os
import uuid
import time
from kiteconnect.exceptions import TokenException

from packages.core.execution.limit_chaser import LimitChaseExecutor, LimitChaseConfig
from packages.core.rate_limiter import LeakyBucketLimiter
from packages.core.compliance import ComplianceGuard
from packages.core.models import Instrument

logger = logging.getLogger("execution_engine")


class SelfMatchException(Exception):
    """Raised when a potential self-match (wash trade) is detected."""
    pass


def plan_client_id(strategy_name: str) -> str:
    """Generate a deterministic client ID for planning."""
    return f"plan_{strategy_name}_{uuid.uuid4().hex[:8]}"


def order_client_id(strategy_name: str, leg: str) -> str:
    """Generate a deterministic client ID for orders."""
    return f"ord_{strategy_name}_{leg}_{uuid.uuid4().hex[:8]}"


@dataclass
class ExecutionConfig:
    """
    Master configuration for the Execution Engine.
    """
    # General
    dry_run: bool = True
    max_retries: int = 3
    freeze_limits: Dict[str, int] = field(default_factory=dict)  # symbol -> max qty per order (DEFAULT key allowed)
    
    # Limit Chase Specifics
    limit_chase_enabled: bool = False
    limit_chase_timeout: float = 10.0
    limit_chase_tick_size: float = 0.05
    limit_chase_step_seconds: float = 1.0
    limit_chase_max_mods: int = 8
    limit_chase_fallback_market: bool = True
    # Note: treating bps as absolute rupee value for now as per updates
    limit_chase_max_slippage_bps: float = 5.0 


@dataclass
class OrderResult:
    """Standardized result for all execution types."""
    success: bool
    order_id: Optional[str]
    filled_qty: int
    avg_price: float
    status: str
    message: str
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpreadLegResult:
    symbol: str
    side: str
    quantity: int
    product: str
    tag: str
    order: OrderResult


@dataclass
class SpreadExecutionResult:
    success: bool
    legs: List[SpreadLegResult]
    failed_leg_index: Optional[int] = None
    message: str = ""


class ExecutionEngine:
    """
    Central facade for all order execution (Standard & Algo).
    
    Compliance features:
    - Rate limiting: Token bucket (<10 OPS per SEBI requirements)
    - Kill switch: Checks trading status before order placement
    """
    def __init__(
        self, 
        kite_client, 
        config: Optional[Any] = None,
        rate_limiter: Optional[LeakyBucketLimiter] = None,
        kill_switch_checker: Optional[Callable[[], bool]] = None,
        compliance_guard: Optional[ComplianceGuard] = None,
        token_refresh_callback: Optional[Callable[[], None]] = None,
        notification_service: Optional[Any] = None
    ):
        self.kite = kite_client
        self.cfg = self._build_config(config)
        self._token_refresh_cb = token_refresh_callback
        self.notification_service = notification_service
        self._notify_trades = os.getenv("NOTIFY_TRADES", "0") == "1"
        self._last_rate_limit_alert = 0.0
        self._last_token_alert = 0.0
        
        # Compliance: Rate limiting (SEBI <10 OPS requirement)
        # Default: 10 orders/sec, burst of 20, per-minute cap of 300
        self.rate_limiter = rate_limiter or LeakyBucketLimiter(
            rate_per_second=10.0,
            rate_per_minute=300.0,  # 5 orders/sec average over minute
            bucket_size=20
        )
        
        # Compliance: Kill switch checker (returns True if trading is paused/killed)
        self._kill_switch_check = kill_switch_checker or (lambda: False)
        
        # Compliance: Shared compliance guard (for use by limit chaser)
        self.compliance_guard = compliance_guard or ComplianceGuard(
            rate_limiter=self.rate_limiter,
            kill_switch_checker=self._kill_switch_check
        )
        
        self.limit_chaser = None
        if self.cfg.limit_chase_enabled:
            self._init_limit_chaser()

    def _ready_to_notify(self, attr: str, cooldown: float) -> bool:
        now = time.time()
        last = getattr(self, attr, 0.0)
        if now - last < cooldown:
            return False
        setattr(self, attr, now)
        return True

    async def _notify(self, level: str, message: str) -> None:
        if not self.notification_service or not self.notification_service.is_configured():
            return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.notification_service.send, message, level)

    def _fire_notification(self, level: str, message: str) -> None:
        """Fire-and-forget notification to avoid blocking order flow."""
        if not self.notification_service or not self.notification_service.is_configured():
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._notify(level, message))
        except RuntimeError:
            # Fallback if event loop not running (should be rare)
            try:
                self.notification_service.send(message, level)
            except Exception:
                logger.warning("Notification send failed outside event loop", exc_info=True)

    def _notify_trade_result(
        self,
        result: "OrderResult",
        symbol: str,
        side: str,
        quantity: int,
        order_type: str,
        price: Optional[float],
        tag: str
    ) -> None:
        """Optional INFO alert on successful trades."""
        if not self._notify_trades or not result.success or self.cfg.dry_run:
            return
        msg = (
            f"Trade placed: {side} {quantity} {symbol} ({order_type}) "
            f"@ {price if price is not None else 'MKT'} | tag={tag} | order_id={result.order_id}"
        )
        self._fire_notification("INFO", msg)

    @staticmethod
    def _enforce_tick_and_lot(instrument: Optional[Instrument], price: Optional[float], qty: int) -> tuple[Optional[float], int]:
        """
        Enforce exchange tick size and lot size (MCX/NFO safety).
        
        Returns possibly adjusted (price, qty).
        """
        if not instrument:
            return price, qty
        
        # Lot size enforcement
        lot = max(int(instrument.lot_size or 1), 1)
        if qty % lot != 0:
            qty = (qty // lot) * lot or lot
        
        # Tick size enforcement for limit/stop-limit
        if price is not None:
            tick = float(instrument.tick_size or 0.05)
            if tick > 0:
                price = round(price / tick) * tick
        
        return price, qty
    
    async def _check_self_match(
        self,
        symbol: str,
        side: str,
        price: Optional[float]
    ) -> None:
        """
        Prevent self-match (wash trade) by checking opposing open orders at same price.
        
        Skips market orders (price=None) and ignores non-open statuses.
        """
        if price is None:
            return
        
        try:
            if not hasattr(self.kite, "orders"):
                return
            import inspect
            orders_fn = self.kite.orders
            open_orders = await orders_fn() if inspect.iscoroutinefunction(orders_fn) else orders_fn()
            if not open_orders:
                return
            
            for order in open_orders:
                try:
                    status = str(order.get("status", "")).upper()
                    if status not in ("OPEN", "TRIGGER PENDING"):
                        continue
                    order_symbol = order.get("tradingsymbol") or order.get("symbol")
                    if order_symbol != symbol:
                        continue
                    order_price = order.get("price")
                    if order_price is None:
                        continue
                    opposing_side = order.get("transaction_type") or order.get("side")
                    if not opposing_side:
                        continue
                    if str(opposing_side).upper() != side.upper() and float(order_price) == float(price):
                        raise SelfMatchException(
                            f"Potential wash trade detected: open {opposing_side} at {order_price} for {symbol}"
                        )
                except SelfMatchException:
                    raise
                except Exception:
                    # Skip malformed order rows
                    continue
        except SelfMatchException:
            raise
        except Exception as e:
            logger.warning("Self-match check skipped", symbol=symbol, error=str(e))
    
    def _apply_algo_tag(self, tag: str) -> str:
        """Ensure regulatory algo ID is attached (max 8 chars for Kite tag)."""
        algo_id = os.getenv("EXCHANGE_ALGO_ID") or os.getenv("SEBI_STRATEGY_ID")
        if not algo_id:
            return tag
        algo_id = str(algo_id)[:8]
        # If original tag already starts with algo_id, keep it
        if tag.startswith(algo_id):
            return tag[:8]
        # Prefer algo id to satisfy compliance; fallback to existing tag if env empty
        return algo_id
    
    def _compute_protection_price(self, side: str, ltp: float) -> float:
        """
        Compute Market Price Protection buffer based on LTP and instrument price tier.
        
        Tiers (percent buffer):
            Options <10: 5%
            Options 10-100: 3%
            Options >100: 2%
            Fallback equities/futures:
                <100: 2%
                100-500: 1%
                >500: 0.5%
        """
        if ltp <= 0:
            return ltp
        if ltp < 10:
            buff = 0.05
        elif ltp < 100:
            buff = 0.03
        elif ltp < 500:
            buff = 0.01
        else:
            buff = 0.005
        if side.upper() == "BUY":
            return ltp * (1 + buff)
        return ltp * (1 - buff)
    
    async def _apply_market_price_protection(
        self,
        symbol: str,
        side: str,
        order_type: str,
        price: Optional[float],
        exchange: Optional[str] = None
    ) -> (str, Optional[float]):
        """
        Convert MARKET to LIMIT with protection price to avoid freak fills.
        """
        if order_type.upper() != "MARKET":
            return order_type, price
        
        # Try to fetch LTP
        ltp = None
        try:
            if hasattr(self.kite, "ltp"):
                exch_prefix = exchange or "NFO"
                instrument_key = symbol if ":" in symbol else f"{exch_prefix}:{symbol}"
                ltp_data = self.kite.ltp([instrument_key])
                if isinstance(ltp_data, dict):
                    item = ltp_data.get(instrument_key) or next(iter(ltp_data.values()))
                    if isinstance(item, dict):
                        ltp = item.get("last_price") or item.get("ltp")
        except Exception:
            ltp = None
        
        if ltp is None:
            logger.warning("MPP fallback: no LTP, leaving as MARKET", symbol=symbol)
            return order_type, price
        
        protection_price = self._compute_protection_price(side, float(ltp))
        logger.info(
            "Applying Market Price Protection",
            symbol=symbol,
            side=side,
            ltp=ltp,
            protection_price=protection_price
        )
        return "LIMIT", protection_price
    
    def _get_freeze_limit(self, symbol: str) -> Optional[int]:
        """Return freeze limit for symbol or DEFAULT."""
        if symbol in self.cfg.freeze_limits:
            return int(self.cfg.freeze_limits[symbol])
        if "DEFAULT" in self.cfg.freeze_limits:
            return int(self.cfg.freeze_limits["DEFAULT"])
        return None
    
    async def _place_sliced_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        product: str,
        order_type: str,
        price: Optional[float],
        tag: str,
        exchange: str
    ) -> OrderResult:
        """
        Slice orders above freeze limit into smaller chunks (sequential).
        """
        limit = self._get_freeze_limit(symbol)
        if not limit or quantity <= limit:
            return await self._place_standard_order(symbol, side, quantity, product, order_type, price, tag, exchange)
        
        slices: List[OrderResult] = []
        remaining = quantity
        while remaining > 0:
            slice_qty = min(remaining, limit)
            result = await self._place_standard_order(symbol, side, slice_qty, product, order_type, price, tag, exchange)
            slices.append(result)
            if not result.success:
                return OrderResult(
                    False,
                    result.order_id,
                    sum(r.filled_qty for r in slices),
                    result.avg_price,
                    result.status,
                    f"Slice failed after {len(slices)} slices: {result.message}"
                )
            remaining -= slice_qty
        
        total_filled = sum(r.filled_qty for r in slices)
        avg_price = sum(r.avg_price * r.filled_qty for r in slices if r.filled_qty) / total_filled if total_filled else price or 0.0
        return OrderResult(
            True,
            slices[-1].order_id if slices else None,
            total_filled,
            avg_price,
            "SLICED_PLACED",
            f"Placed in {len(slices)} slices"
        )

    def _init_limit_chaser(self):
        """Derive LimitChaseConfig from ExecutionConfig."""
        chase_cfg = LimitChaseConfig(
            tick_size=self.cfg.limit_chase_tick_size,
            max_slippage_abs=self.cfg.limit_chase_max_slippage_bps, # Using absolute override
            max_roundtrip_seconds=self.cfg.limit_chase_timeout,
            step_seconds=self.cfg.limit_chase_step_seconds,
            max_modifications=self.cfg.limit_chase_max_mods,
            fallback_to_market=self.cfg.limit_chase_fallback_market,
            verbose_logging=True
        )
        # Pass compliance guard to limit chaser
        self.limit_chaser = LimitChaseExecutor(self.kite, chase_cfg, compliance_guard=self.compliance_guard)
        logger.info("Limit Chase Executor Initialized")

    def _build_config(self, config: Optional[Any]) -> ExecutionConfig:
        """Normalize config input to internal ExecutionConfig."""
        if isinstance(config, ExecutionConfig):
            return config
        
        source: Dict[str, Any] = {}
        if isinstance(config, dict):
            source = config
        elif config is not None:
            source = {
                key: getattr(config, key)
                for key in dir(config)
                if not key.startswith("_") and hasattr(config, key)
            }
        
        def get_value(*names, default):
            for name in names:
                if name in source:
                    return source[name]
            return default
        
        return ExecutionConfig(
            dry_run=bool(get_value("dry_run", default=True)),
            max_retries=int(get_value("max_retries", "max_order_retries", default=3)),
            limit_chase_enabled=bool(
                get_value("limit_chase_enabled", "use_limit_chase", default=False)
            ),
            limit_chase_timeout=float(
                get_value("limit_chase_timeout", "limit_chase_timeout_ms", default=10.0)
            ),
            limit_chase_tick_size=float(
                get_value("limit_chase_tick_size", "tick_size", default=0.05)
            ),
            limit_chase_step_seconds=float(
                get_value("limit_chase_step_seconds", "chase_step_seconds", default=1.0)
            ),
            limit_chase_max_mods=int(
                get_value("limit_chase_max_mods", "limit_chase_max_chases", default=8)
            ),
            limit_chase_fallback_market=bool(
                get_value("limit_chase_fallback_market", "fallback_to_market", default=True)
            ),
            limit_chase_max_slippage_bps=float(
                get_value("limit_chase_max_slippage_bps", default=5.0)
            ),
            freeze_limits=dict(get_value("freeze_limits", default={})),
        )

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        product: str = "NRML",
        order_type: str = "MARKET",
        price: Optional[float] = None,
        tag: str = "EXEC",
        use_limit_chase: bool = False,
        emergency_bypass: bool = False,
        instrument: Optional[Instrument] = None
    ) -> OrderResult:
        """
        Public API to place orders. Routes to Limit Chase if requested and enabled.
        
        Compliance checks:
        1. Kill switch: Blocks if trading is paused/killed
        2. Self-match: Prevents wash trades (opposing open order at same price)
        2. Rate limiting: Enforces <10 OPS SEBI requirement
        """
        try:
            tag = self._apply_algo_tag(tag)
            
            # Compliance: Kill switch check (unless emergency bypass)
            if not emergency_bypass and self._kill_switch_check():
                logger.warning(f"[{tag}] Order blocked: Kill switch active", symbol=symbol, side=side)
                return OrderResult(
                    False, None, 0, 0.0, "BLOCKED", 
                    "Trading paused/kill switch active"
                )
            
            # Enforce tick/lot using instrument metadata (MCX/NFO safety)
            price, quantity = self._enforce_tick_and_lot(instrument, price, quantity)
            
            # Exchange and product defaults (MCX aware)
            exchange = (instrument.exchange if instrument and instrument.exchange else None) or "NFO"
            if instrument and instrument.exchange == "MCX" and (not product or product == "NRML"):
                product = getattr(self.cfg, "mcx_product", product or "NRML")

            # Compliance: Self-match (wash trade) prevention for limit orders
            if order_type and order_type.upper() == "LIMIT":
                await self._check_self_match(symbol=symbol, side=side, price=price)
            
            # Market Price Protection: convert MARKET to LIMIT with buffer
            order_type, price = await self._apply_market_price_protection(symbol, side, order_type, price, exchange=exchange)
            
            # Compliance: Rate limiting (SEBI <10 OPS)
            # Always enforce rate limiting, even in emergency (to avoid API rate limit errors)
            if not await self.rate_limiter.acquire(limiter_type="order_placement"):
                logger.warning(
                    f"[{tag}] Order rate limited: Exceeded 10 OPS threshold",
                    symbol=symbol,
                    side=side,
                    emergency_bypass=emergency_bypass
                )
                if self._ready_to_notify("_last_rate_limit_alert", cooldown=60.0):
                    self._fire_notification(
                        "ERROR",
                        f"Rate limit hit for {symbol} ({tag}); order blocked to stay under 10 OPS guard"
                    )
                return OrderResult(
                    False, None, 0, 0.0, "RATE_LIMITED",
                    "Order rate limit exceeded (<10 OPS SEBI requirement)"
                )
            
            # 1. Algo Execution (Limit Chase)
            if self.limit_chaser and ((use_limit_chase) or (order_type.upper() == "LIMIT")):
                result = await self._place_entry_with_limit_chase(
                    symbol, side, quantity, product, tag, exchange
                )
            else:
                # 2. Standard Execution
                result = await self._place_sliced_order(
                    symbol, side, quantity, product, order_type, price, tag, exchange
                )

            self._notify_trade_result(result, symbol, side, quantity, order_type, price, tag)
            return result

        except Exception as e:
            logger.error(f"[{tag}] Execution Failed: {e}", exc_info=True)
            return OrderResult(False, None, 0, 0.0, "ERROR", str(e))

    async def execute_spread_order(
        self,
        legs: List[Dict[str, Any]],
        *,
        tag_prefix: str = "SPREAD",
        rollback_on_fail: bool = True,
    ) -> SpreadExecutionResult:
        """
        Execute multiple legs atomically with rollback safety.

        Args:
            legs: List of leg definitions containing symbol, side, quantity,
                  and optional product/tag/use_limit_chase.
            tag_prefix: Base tag applied when a custom tag isn't provided.
            rollback_on_fail: If True, previously filled legs are hedged out
                              when a later leg fails.
        """
        if not legs:
            return SpreadExecutionResult(True, [], None, "No legs provided")

        normalized: List[Dict[str, Any]] = []
        for idx, leg in enumerate(legs):
            try:
                symbol = leg["symbol"]
                side = leg["side"]
                quantity = int(leg["quantity"])
            except KeyError as missing:
                raise ValueError(f"Spread leg missing required field: {missing}") from missing

            normalized.append(
                {
                    "symbol": symbol,
                    "side": side.upper(),
                    "quantity": quantity,
                    "product": leg.get("product", "NRML"),
                    "tag": leg.get("tag") or f"{tag_prefix}_LEG{idx + 1}",
                    "use_limit_chase": leg.get("use_limit_chase", False),
                }
            )

        leg_results: List[SpreadLegResult] = []
        executed_successfully: List[SpreadLegResult] = []

        for idx, leg in enumerate(normalized):
            order = await self.place_order(
                symbol=leg["symbol"],
                side=leg["side"],
                quantity=leg["quantity"],
                product=leg["product"],
                order_type="MARKET",
                price=None,
                tag=leg["tag"],
                use_limit_chase=leg["use_limit_chase"],
                instrument=leg.get("instrument")
            )

            leg_result = SpreadLegResult(
                symbol=leg["symbol"],
                side=leg["side"],
                quantity=leg["quantity"],
                product=leg["product"],
                tag=leg["tag"],
                order=order,
            )
            leg_results.append(leg_result)

            if not order.success:
                message = f"Leg {leg['symbol']} failed: {order.message}"
                if rollback_on_fail and executed_successfully:
                    await self._rollback_legs(executed_successfully)
                return SpreadExecutionResult(False, leg_results, idx, message)

            executed_successfully.append(leg_result)

        return SpreadExecutionResult(True, leg_results, None, "Spread executed")

    async def _place_entry_with_limit_chase(
        self,
        symbol: str,
        side: str,
        quantity: int,
        product: str,
        tag: str,
        exchange: str
    ) -> OrderResult:
        """
        Proxies the request to LimitChaseExecutor and maps the result.
        """
        logger.info(f"[{tag}] Handing off to Limit Chaser...")
        
        # Call the actual signature of LimitChaseExecutor.execute
        result = await self.limit_chaser.execute_limit_chase(
            symbol=symbol,
            side=side,
            quantity=quantity,
            product=product,
            variety="regular",
            tag=tag,
            meta={"exchange": exchange}
        )

        # Map LimitChaseResult -> OrderResult
        return OrderResult(
            success=result.filled,
            order_id=result.order_id,
            filled_qty=result.filled_qty,
            avg_price=result.avg_price,
            status=result.status,
            message=result.message,
            meta={"strategy": "limit_chase", "phases": result.message}
        )

    async def _cancel_open_orders_for_symbol(self, symbol: str) -> None:
        """
        Best-effort cancel of open/trigger-pending orders for a symbol before closing it.
        Prevents stale SL/TP legs from flipping net exposure after an exit.
        """
        if not hasattr(self.kite, "orders") or not hasattr(self.kite, "cancel_order"):
            return
        try:
            import inspect
            orders_fn = self.kite.orders
            orders = await orders_fn() if inspect.iscoroutinefunction(orders_fn) else orders_fn()
            if not orders:
                return
            for order in orders:
                status = str(order.get("status", "")).upper()
                if status not in ("OPEN", "TRIGGER PENDING"):
                    continue
                order_symbol = order.get("tradingsymbol") or order.get("symbol")
                if order_symbol != symbol:
                    continue
                order_id = order.get("order_id") or order.get("id")
                if not order_id:
                    continue
                variety = order.get("variety", "regular")
                cancel_fn = self.kite.cancel_order
                try:
                    await cancel_fn(variety=variety, order_id=order_id) if inspect.iscoroutinefunction(cancel_fn) else cancel_fn(variety=variety, order_id=order_id)
                    logger.info("Cancelled stale order before exit", symbol=symbol, order_id=order_id, status=status)

                    # SEBI Compliance: Audit log for order cancellation
                    try:
                        from packages.storage.database import get_db_session
                        from packages.storage.models import AuditLog, AuditActionEnum
                        async with get_db_session() as session:
                            audit_log = AuditLog(
                                action=AuditActionEnum.ORDER_CANCELLED,
                                level="INFO",
                                category="EXEC",
                                message=f"Order cancelled: {symbol} (order_id={order_id})",
                                details={
                                    "order_id": order_id,
                                    "symbol": symbol,
                                    "variety": variety,
                                    "reason": "stale_order_cleanup"
                                }
                            )
                            session.add(audit_log)
                            await session.commit()
                    except Exception as audit_err:
                        logger.warning("Failed to write ORDER_CANCELLED audit log", error=str(audit_err))

                except Exception as cancel_err:
                    logger.warning("Could not cancel stale order", symbol=symbol, order_id=order_id, error=str(cancel_err))
        except Exception as e:
            logger.warning("Failed to scan/cancel open orders before exit", symbol=symbol, error=str(e))

    async def close_position(self, position: Any, reason: str = "EXIT") -> OrderResult:
        """
        Close an open position by submitting a market order on the opposite side.
        
        - Uses the instrument's tradingsymbol when available (falls back to symbol attr).
        - Determines exit side from the position's side (LONG/BUY -> SELL, else BUY).
        """
        symbol = None
        if hasattr(position, "instrument") and position.instrument:
            symbol = getattr(position.instrument, "tradingsymbol", None) or getattr(position.instrument, "symbol", None)
        if not symbol:
            symbol = getattr(position, "symbol", None)
        qty = abs(getattr(position, "quantity", 0) or getattr(position, "qty", 0) or 0)
        if not symbol or qty <= 0:
            return OrderResult(False, None, 0, 0.0, "ERROR", "Missing symbol or quantity for exit")
        
        # Cancel sibling SL/TP legs to avoid net flip after exit
        await self._cancel_open_orders_for_symbol(symbol)
        
        side_val = getattr(getattr(position, "side", None), "value", getattr(position, "side", None))
        side_str = str(side_val).upper() if side_val else ""
        exit_side = "SELL" if side_str in ("LONG", "BUY") else "BUY"
        tag = f"{reason.upper()}_EXIT" if reason else "EXIT"
        
        return await self.place_order(
            symbol=symbol,
            side=exit_side,
            quantity=qty,
            product="NRML",
            order_type="MARKET",
            price=None,
            tag=tag,
            instrument=None
        )

    async def _place_standard_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        product: str,
        order_type: str,
        price: Optional[float],
        tag: str,
        exchange: str
    ) -> OrderResult:
        """Internal wrapper for standard Kite place_order."""
        try:
            if self.cfg.dry_run:
                logger.info(f"[{tag}] DRY RUN: {side} {quantity} {symbol}", exchange=exchange, price=price)
                return OrderResult(True, "DRY_ID", quantity, price or 0.0, "FILLED", "Dry Run")

            order_id = self.kite.place_order(
                variety="regular",
                exchange=exchange,
                tradingsymbol=symbol,
                transaction_type=side,
                quantity=quantity,
                product=product,
                order_type=order_type,
                price=price,
                tag=tag
            )

            # SEBI Compliance: Audit log for order placement
            if order_id:
                try:
                    from packages.storage.database import get_db_session
                    from packages.storage.models import AuditLog, AuditActionEnum
                    async with get_db_session() as session:
                        audit_log = AuditLog(
                            action=AuditActionEnum.ORDER_PLACED,
                            level="INFO",
                            category="EXEC",
                            message=f"Order placed: {side} {quantity} {symbol}",
                            details={
                                "order_id": order_id,
                                "symbol": symbol,
                                "side": side,
                                "quantity": quantity,
                                "product": product,
                                "order_type": order_type,
                                "price": price,
                                "tag": tag,
                                "exchange": exchange
                            }
                        )
                        session.add(audit_log)
                        await session.commit()
                except Exception as audit_err:
                    logger.warning("Failed to write ORDER_PLACED audit log", error=str(audit_err))

                return OrderResult(True, order_id, quantity, price or 0.0, "OPEN", "Placed")
            return OrderResult(False, None, 0, 0.0, "FAILED", "No Order ID")
        except TokenException as e:
            logger.warning("Token exception during place_order, attempting refresh", error=str(e))
            if self._ready_to_notify("_last_token_alert", cooldown=180.0):
                self._fire_notification(
                    "ERROR",
                    f"Access token invalid during order placement for {symbol} ({tag}); attempting refresh"
                )
            if self._token_refresh_cb:
                try:
                    self._token_refresh_cb()
                    # Retry once after refresh
                    order_id = self.kite.place_order(
                        variety="regular",
                        exchange=exchange,
                        tradingsymbol=symbol,
                        transaction_type=side,
                        quantity=quantity,
                        product=product,
                        order_type=order_type,
                        price=price,
                        tag=tag
                    )
                    if order_id:
                        return OrderResult(True, order_id, quantity, price or 0.0, "OPEN", "Placed")
                    return OrderResult(False, None, 0, 0.0, "FAILED", "No Order ID after refresh")
                except Exception as retry_error:
                    logger.error("place_order failed after token refresh", error=str(retry_error))
                    if self._ready_to_notify("_last_token_alert", cooldown=180.0):
                        self._fire_notification(
                            "ERROR",
                            f"Order placement failed after token refresh for {symbol} ({tag}): {retry_error}"
                        )
                    return OrderResult(False, None, 0, 0.0, "ERROR", str(retry_error))
            logger.error("Token exception with no refresh callback", error=str(e))
            return OrderResult(False, None, 0, 0.0, "AUTH_ERROR", str(e))
        except Exception as e:
            raise e

    async def _rollback_legs(self, executed_legs: List[SpreadLegResult]) -> None:
        """Attempt to flatten previously executed legs in reverse order."""
        for leg in reversed(executed_legs):
            rollback_side = "SELL" if leg.side == "BUY" else "BUY"
            rollback_tag = f"{leg.tag}_RLBK"
            try:
                await self.place_order(
                    symbol=leg.symbol,
                    side=rollback_side,
                    quantity=leg.quantity,
                    product=leg.product,
                    order_type="MARKET",
                    price=None,
                    tag=rollback_tag,
                    use_limit_chase=False,
                )
                logger.info(
                    "[ExecutionEngine] Rolled back leg %s (%s) via %s",
                    leg.symbol,
                    leg.side,
                    rollback_tag,
                )
            except Exception as e:
                logger.error(
                    "[ExecutionEngine] Rollback failed for %s (%s): %s",
                    leg.symbol,
                    leg.side,
                    e,
                    exc_info=True,
                )
    
    def get_limit_chase_stats(self) -> Dict[str, Any]:
        """
        Get execution alpha telemetry from LimitChaseExecutor.
        
        Returns:
            Dictionary with execution stats, or empty dict if limit chase not enabled.
        """
        if not self.limit_chaser:
            return {}
        return self.limit_chaser.get_stats()
