"""Limit Chase Execution Engine - Execution Alpha through Intelligent Order Management

This module implements a "Limit Chase" algorithm that:
1. Places LIMIT orders at Best Bid/Ask (captures spread instead of paying it)
2. Chases the price if not filled within timeout (500ms default)
3. Protects against excessive slippage
4. Provides execution alpha over simple MARKET orders

Usage:
    chaser = LimitChaseExecutor(kite_client, LimitChaseConfig())
    result = await chaser.execute_limit_chase(
        symbol="NIFTY24NOV24000CE",
        side="SELL",
        quantity=25,
        product="MIS",
        tag="STRATEGY_ENTRY"
    )
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Literal, Dict, Any
import asyncio
import time
import structlog

logger = structlog.get_logger(__name__)

Side = Literal["BUY", "SELL"]


@dataclass
class LimitChaseConfig:
    """
    Configuration for the limit chase execution engine.
    """
    tick_size: float = 0.05               # NSE options tick
    max_slippage_abs: float = 5.0         # Rs away from anchor allowed
    max_roundtrip_seconds: float = 8.0    # overall timeout
    step_seconds: float = 0.7             # wait between checks/modifies
    max_modifications: int = 8            # safety bound
    fallback_to_market: bool = False      # if True, send MARKET at the end
    verbose_logging: bool = True


@dataclass
class LimitChaseResult:
    """Result of a limit chase execution"""
    filled: bool
    order_id: Optional[str]
    filled_qty: int
    avg_fill_price: Optional[float]
    status: str          # "FILLED", "CANCELLED", "TIMEOUT", "SLIPPAGE_GUARD", "ERROR"
    message: str = ""


class LimitChaseExecutor:
    """
    Execution alpha layer:
      - Start with best bid/ask in your favor
      - If not filled, chase slowly up/down the book
      - Enforce slippage + time guards
    """

    def __init__(self, kite_client, cfg: Optional[LimitChaseConfig] = None):
        self.kite = kite_client
        self.cfg = cfg or LimitChaseConfig()
        
        # Telemetry: Track execution alpha
        self.stats = {
            "attempts": 0,
            "fills": 0,
            "timeouts": 0,
            "slippage_stops": 0,
            "errors": 0,
            "saved_slippage_rs": 0.0,  # naive MKT vs achieved
        }

    # ---- Public API -----------------------------------------------------

    async def execute(
        self,
        symbol: str,
        side: Side,
        quantity: int,
        tag: str = "CHASE",
        product: str = "NRML"
    ) -> LimitChaseResult:
        """
        Wrapper for execute_limit_chase() for compatibility with ExecutionEngine.
        """
        return await self.execute_limit_chase(
            symbol=symbol,
            side=side,
            quantity=quantity,
            product=product,
            variety="regular",
            tag=tag,
            meta={}
        )

    async def execute_limit_chase(
        self,
        *,
        symbol: str,
        side: Side,
        quantity: int,
        product: str,
        variety: str = "regular",
        tag: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> LimitChaseResult:
        """
        Main entrypoint for strategies.

        - Returns LimitChaseResult
        - Never raises unless something truly unexpected happens
        """
        self.stats["attempts"] += 1
        
        try:
            return await self._execute(symbol, side, quantity, product, variety, tag, meta or {})
        except Exception as e:
            logger.error(
                f"[LimitChase] Fatal error for {symbol} {side} x{quantity}: {e}",
                exc_info=True,
            )
            self.stats["errors"] += 1
            return LimitChaseResult(
                filled=False,
                order_id=None,
                filled_qty=0,
                avg_fill_price=None,
                status="ERROR",
                message=str(e),
            )

    # ---- Internal helpers -----------------------------------------------

    async def _execute(
        self,
        symbol: str,
        side: Side,
        quantity: int,
        product: str,
        variety: str,
        tag: Optional[str],
        meta: Dict[str, Any],
    ) -> LimitChaseResult:
        cfg = self.cfg
        t0 = time.time()

        # 1) Get initial quote + anchor
        quote = await self._safe_quote(symbol)
        if quote is None:
            return LimitChaseResult(
                filled=False,
                order_id=None,
                filled_qty=0,
                avg_fill_price=None,
                status="ERROR",
                message="Failed to fetch initial quote",
            )

        anchor_price, first_limit = self._derive_initial_prices(side, quote)
        if cfg.verbose_logging:
            logger.info(
                "[LimitChase] Start %s %s x%d | anchor=%.2f limit=%.2f",
                side, symbol, quantity, anchor_price, first_limit,
            )

        # 2) Place first LIMIT order
        order_id = await self._safe_place_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=first_limit,
            product=product,
            variety=variety,
            tag=tag,
            meta=meta,
        )
        if order_id is None:
            return LimitChaseResult(
                filled=False,
                order_id=None,
                filled_qty=0,
                avg_fill_price=None,
                status="ERROR",
                message="Initial place_order failed",
            )

        working_price = first_limit
        num_mods = 0

        # 3) Chase loop
        while True:
            await asyncio.sleep(cfg.step_seconds)

            elapsed = time.time() - t0
            if elapsed >= cfg.max_roundtrip_seconds or num_mods >= cfg.max_modifications:
                # Timeout -> either cancel or fallback to market
                self.stats["timeouts"] += 1
                if cfg.fallback_to_market:
                    logger.info(
                        "[LimitChase] Timeout, switching to MARKET for %s %s x%d",
                        side, symbol, quantity,
                    )
                    await self._safe_cancel(order_id)
                    mkt_order_id = await self._safe_place_order(
                        symbol=symbol,
                        side=side,
                        quantity=quantity,
                        price=None,
                        product=product,
                        variety=variety,
                        tag=tag,
                        meta={**meta, "limit_chase_fallback": True},
                        order_type="MARKET",
                    )
                    # We don't chase MARKET further, just report
                    return LimitChaseResult(
                        filled=True if mkt_order_id else False,
                        order_id=mkt_order_id,
                        filled_qty=quantity if mkt_order_id else 0,
                        avg_fill_price=None,
                        status="TIMEOUT",
                        message="Timeout reached, fallback_to_market executed",
                    )
                else:
                    await self._safe_cancel(order_id)
                    return LimitChaseResult(
                        filled=False,
                        order_id=order_id,
                        filled_qty=0,
                        avg_fill_price=None,
                        status="TIMEOUT",
                        message="Timeout reached, order cancelled",
                    )

            # 3a) Check order status
            ord_info = await self._safe_get_order(order_id)
            if ord_info is None:
                # can't see order; try cancel + bail
                await self._safe_cancel(order_id)
                return LimitChaseResult(
                    filled=False,
                    order_id=order_id,
                    filled_qty=0,
                    avg_fill_price=None,
                    status="ERROR",
                    message="Order status unavailable; cancelled defensively",
                )

            filled_qty, avg_fill_price, status = self._extract_fill_info(ord_info)
            if status in ("COMPLETE", "FILLED") or filled_qty >= quantity:
                # Calculate saved slippage (naive market vs actual fill)
                final_price = avg_fill_price or working_price
                naive_mkt_price = anchor_price  # what you would've paid with naive MKT
                saved = 0.0
                
                if side == "BUY":
                    saved = max(0.0, naive_mkt_price - final_price) * filled_qty
                else:  # SELL
                    saved = max(0.0, final_price - naive_mkt_price) * filled_qty
                
                self.stats["fills"] += 1
                self.stats["saved_slippage_rs"] += saved
                
                if cfg.verbose_logging:
                    logger.info(
                        "[LimitChase] FILLED %s %s x%d @ %.2f (saved ₹%.2f)",
                        side, symbol, filled_qty, final_price, saved,
                    )
                return LimitChaseResult(
                    filled=True,
                    order_id=order_id,
                    filled_qty=filled_qty,
                    avg_fill_price=final_price,
                    status="FILLED",
                    message="Filled via limit chase",
                )

            # 3b) Partial fills: adjust remaining qty or just keep chase for remainder
            remaining_qty = max(quantity - filled_qty, 0)
            if remaining_qty <= 0:
                return LimitChaseResult(
                    filled=True,
                    order_id=order_id,
                    filled_qty=filled_qty,
                    avg_fill_price=avg_fill_price or working_price,
                    status="FILLED",
                    message="Fully filled (partial+partial)",
                )

            # 3c) Refresh quote, see if we should slide
            quote = await self._safe_quote(symbol)
            if quote is None:
                continue  # transient, next loop

            best_price = self._best_price_for_side(side, quote)
            if best_price is None:
                continue

            # slippage guard
            if abs(best_price - anchor_price) > cfg.max_slippage_abs:
                self.stats["slippage_stops"] += 1
                if cfg.verbose_logging:
                    logger.warning(
                        "[LimitChase] Slippage guard triggered for %s %s: best=%.2f, anchor=%.2f",
                        side, symbol, best_price, anchor_price,
                    )
                await self._safe_cancel(order_id)
                return LimitChaseResult(
                    filled=False,
                    order_id=order_id,
                    filled_qty=filled_qty,
                    avg_fill_price=avg_fill_price,
                    status="SLIPPAGE_GUARD",
                    message="Cancelled due to slippage guard",
                )

            new_price = self._nudge_towards(best_price, side)
            if self._price_eq(new_price, working_price, cfg.tick_size):
                continue  # nothing to do

            # modify order (for remaining qty)
            ok = await self._safe_modify(order_id, price=new_price)
            if ok:
                working_price = new_price
                num_mods += 1
                if cfg.verbose_logging:
                    logger.info(
                        "[LimitChase] Modify %s %s: price %.2f -> %.2f (mods=%d)",
                        side, symbol, working_price, new_price, num_mods,
                    )

    # ---- Broker helpers (adapt to your KiteClient) ----------------------

    async def _safe_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote from broker, with error handling"""
        try:
            # Try async quote first
            if hasattr(self.kite, 'quote') and hasattr(self.kite.quote, '__call__'):
                import inspect
                if inspect.iscoroutinefunction(self.kite.quote):
                    return await self.kite.quote(symbol)
                else:
                    # Sync method - wrap in executor if needed
                    return self.kite.quote(symbol)
            
            # Fallback: try ltp and build minimal quote
            if hasattr(self.kite, 'ltp'):
                instrument_key = f"NFO:{symbol}"  # Adjust exchange as needed
                ltp_data = self.kite.ltp([instrument_key])
                if isinstance(ltp_data, dict) and instrument_key in ltp_data:
                    price_data = ltp_data[instrument_key]
                    if isinstance(price_data, dict):
                        ltp = price_data.get("last_price", 0.0)
                    else:
                        ltp = float(price_data) if price_data else 0.0
                    
                    # Build minimal quote structure
                    return {
                        "last_price": ltp,
                        "ltp": ltp,
                        "depth": {
                            "buy": [{"price": ltp}],
                            "sell": [{"price": ltp}],
                        }
                    }
            
            return None
        except Exception as e:
            logger.debug(f"[LimitChase] quote() failed for {symbol}: {e}")
            return None

    async def _safe_place_order(
        self,
        *,
        symbol: str,
        side: Side,
        quantity: int,
        price: Optional[float],
        product: str,
        variety: str,
        tag: Optional[str],
        meta: Dict[str, Any],
        order_type: str = "LIMIT",
    ) -> Optional[str]:
        """Place order via broker, with error handling"""
        try:
            # Try async place_order first
            if hasattr(self.kite, 'place_order'):
                import inspect
                if inspect.iscoroutinefunction(self.kite.place_order):
                    order_id = await self.kite.place_order(
                        symbol=symbol,
                        side=side,
                        quantity=quantity,
                        order_type=order_type,
                        price=price,
                        product=product,
                        variety=variety,
                        tag=tag,
                        meta=meta,
                    )
                else:
                    # Sync method
                    order_id = self.kite.place_order(
                        exchange="NFO",  # Adjust as needed
                        tradingsymbol=symbol,
                        transaction_type=side,
                        quantity=quantity,
                        order_type=order_type,
                        price=price,
                        product=product,
                        variety=variety,
                        tag=tag,
                    )
                    # Kite returns dict with order_id
                    if isinstance(order_id, dict):
                        order_id = order_id.get("order_id")
                
                return str(order_id) if order_id else None
            
            return None
        except Exception as e:
            logger.error(f"[LimitChase] place_order failed for {symbol} {side}: {e}", exc_info=True)
            return None

    async def _safe_modify(self, order_id: str, price: float) -> bool:
        """Modify order price, with error handling"""
        try:
            if hasattr(self.kite, 'modify_order'):
                import inspect
                if inspect.iscoroutinefunction(self.kite.modify_order):
                    await self.kite.modify_order(order_id=order_id, price=price)
                else:
                    self.kite.modify_order(variety="regular", order_id=order_id, price=price)
                return True
            return False
        except Exception as e:
            logger.debug(f"[LimitChase] modify_order failed for {order_id}: {e}")
            return False

    async def _safe_cancel(self, order_id: str) -> bool:
        """Cancel order, with error handling"""
        try:
            if hasattr(self.kite, 'cancel_order'):
                import inspect
                if inspect.iscoroutinefunction(self.kite.cancel_order):
                    await self.kite.cancel_order(order_id=order_id)
                else:
                    self.kite.cancel_order(variety="regular", order_id=order_id)
                return True
            return False
        except Exception as e:
            logger.debug(f"[LimitChase] cancel_order failed for {order_id}: {e}")
            return False

    async def _safe_get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order status, with error handling"""
        try:
            if hasattr(self.kite, 'orders'):
                # Get all orders and find ours
                orders = self.kite.orders()
                for order in orders:
                    if str(order.get("order_id")) == str(order_id):
                        return order
            elif hasattr(self.kite, 'get_order'):
                import inspect
                if inspect.iscoroutinefunction(self.kite.get_order):
                    return await self.kite.get_order(order_id)
                else:
                    return self.kite.get_order(order_id)
            return None
        except Exception as e:
            logger.debug(f"[LimitChase] get_order failed for {order_id}: {e}")
            return None

    # ---- Price helpers --------------------------------------------------

    def _derive_initial_prices(self, side: Side, quote: Dict[str, Any]) -> tuple[float, float]:
        """
        Returns (anchor_price, first_limit_price).
        anchor = last traded price, or mid; limit = best_bid/ask in your favor.
        """
        ltp = float(quote.get("last_price") or quote.get("ltp") or 0.0)
        best_bid = self._best_bid(quote) or ltp
        best_ask = self._best_ask(quote) or ltp

        if side == "BUY":
            first_limit = best_bid  # buy at bid
        else:
            first_limit = best_ask  # sell at ask

        return ltp, self._round_to_tick(first_limit, self.cfg.tick_size)

    def _best_bid(self, quote: Dict[str, Any]) -> Optional[float]:
        """Extract best bid from quote"""
        depth = quote.get("depth") or {}
        bids = depth.get("buy") or depth.get("bids") or []
        if not bids:
            return None
        return float(bids[0].get("price", 0.0))

    def _best_ask(self, quote: Dict[str, Any]) -> Optional[float]:
        """Extract best ask from quote"""
        depth = quote.get("depth") or {}
        asks = depth.get("sell") or depth.get("asks") or []
        if not asks:
            return None
        return float(asks[0].get("price", 0.0))

    def _best_price_for_side(self, side: Side, quote: Dict[str, Any]) -> Optional[float]:
        """Get best price for given side"""
        return self._best_bid(quote) if side == "BUY" else self._best_ask(quote)

    def _nudge_towards(self, best_price: float, side: Side) -> float:
        """
        Small nudge: 1 tick beyond current best to increase fill probability.
        For BUY, price = best_ask + 1 tick; for SELL, price = best_bid - 1 tick.
        """
        tick = self.cfg.tick_size
        if side == "BUY":
            candidate = best_price + tick
        else:
            candidate = best_price - tick
        return self._round_to_tick(candidate, tick)

    @staticmethod
    def _round_to_tick(price: float, tick: float) -> float:
        """Round price to nearest tick"""
        if tick <= 0:
            return price
        return round(price / tick) * tick

    @staticmethod
    def _extract_fill_info(order: Dict[str, Any]) -> tuple[int, Optional[float], str]:
        """Extract fill information from order dict"""
        filled_qty = int(order.get("filled_quantity") or order.get("filled_qty") or 0)
        avg_fill_price = order.get("average_price") or order.get("avg_price")
        status = (order.get("status") or "").upper()
        return filled_qty, (float(avg_fill_price) if avg_fill_price is not None else None), status

    @staticmethod
    def _price_eq(a: float, b: float, tick: float) -> bool:
        """Check if two prices are equal within tick tolerance"""
        if tick <= 0:
            return abs(a - b) < 1e-4
        return abs(a - b) < (tick / 2.0)
    
    def get_stats(self) -> Dict[str, float | int]:
        """
        Get execution alpha telemetry stats.
        
        Returns:
            Dictionary with:
            - attempts: Total number of limit chase attempts
            - fills: Number of successful fills
            - timeouts: Number of timeouts (with or without fallback)
            - slippage_stops: Number of times slippage guard triggered
            - errors: Number of errors
            - saved_slippage_rs: Total rupees saved vs naive market orders
        """
        return dict(self.stats)
