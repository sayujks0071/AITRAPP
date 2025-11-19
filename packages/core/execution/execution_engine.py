from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import logging
import uuid

from packages.core.execution.limit_chaser import LimitChaseExecutor, LimitChaseConfig

logger = logging.getLogger("execution_engine")


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
    dry_run: bool = False
    max_retries: int = 3
    
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
    """
    def __init__(self, kite_client, config: Optional[Any] = None):
        self.kite = kite_client
        self.cfg = self._build_config(config)
        
        self.limit_chaser = None
        if self.cfg.limit_chase_enabled:
            self._init_limit_chaser()

    def _init_limit_chaser(self):
        """Derive LimitChaseConfig from ExecutionConfig."""
        chase_cfg = LimitChaseConfig(
            tick_size=self.cfg.limit_chase_tick_size,
            max_slippage_abs=self.cfg.limit_chase_max_slippage_bps, # Using absolute override
            max_roundtrip_seconds=self.cfg.limit_chase_timeout,
            step_seconds=self.cfg.limit_chase_step_seconds,
            max_modifications=self.cfg.limit_chase_max_mods,
            fallback_to_market=self.cfg.limit_chase_fallback_market,
            verbose=True
        )
        self.limit_chaser = LimitChaseExecutor(self.kite, chase_cfg)
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
            dry_run=bool(get_value("dry_run", default=False)),
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
        use_limit_chase: bool = False
    ) -> OrderResult:
        """
        Public API to place orders. Routes to Limit Chase if requested and enabled.
        """
        try:
            # 1. Algo Execution (Limit Chase)
            if use_limit_chase and self.limit_chaser:
                return await self._place_entry_with_limit_chase(
                    symbol, side, quantity, product, tag
                )

            # 2. Standard Execution
            return await self._place_standard_order(
                symbol, side, quantity, product, order_type, price, tag
            )

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
        tag: str
    ) -> OrderResult:
        """
        Proxies the request to LimitChaseExecutor and maps the result.
        """
        logger.info(f"[{tag}] Handing off to Limit Chaser...")
        
        # Call the actual signature of LimitChaseExecutor.execute
        result = await self.limit_chaser.execute(
            symbol=symbol,
            side=side,
            quantity=quantity,
            tag=tag,
            product=product
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

    async def _place_standard_order(
        self, symbol, side, quantity, product, order_type, price, tag
    ) -> OrderResult:
        """Internal wrapper for standard Kite place_order."""
        try:
            if self.cfg.dry_run:
                logger.info(f"[{tag}] DRY RUN: {side} {quantity} {symbol}")
                return OrderResult(True, "DRY_ID", quantity, price or 0.0, "FILLED", "Dry Run")

            order_id = await self.kite.place_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                price=price,
                product=product,
                tag=tag
            )
            
            if order_id:
                return OrderResult(True, order_id, quantity, price or 0.0, "OPEN", "Placed")
            return OrderResult(False, None, 0, 0.0, "FAILED", "No Order ID")

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
