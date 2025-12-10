"""Position adjustment logic for handling partial fills and leg failures in spread orders"""
import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import structlog

from packages.core.execution.execution_engine import SpreadExecutionResult, SpreadLegResult, OrderResult

logger = structlog.get_logger(__name__)


class AdjustmentStrategy(str, Enum):
    """Strategy for handling partial fills"""
    RETRY_FAILED = "RETRY_FAILED"  # Retry failed legs up to max attempts
    ROLLBACK_ALL = "ROLLBACK_ALL"  # Rollback all successful legs (original behavior)
    KEEP_PARTIAL = "KEEP_PARTIAL"  # Keep successful legs as positions
    HEDGE_PARTIAL = "HEDGE_PARTIAL"  # Add hedge for unmatched legs


@dataclass
class PartialFillState:
    """Tracks the state of a partially filled spread order"""
    original_legs: List[Dict[str, Any]]
    executed_legs: List[SpreadLegResult]
    failed_legs: List[Dict[str, Any]]
    retry_count: int = 0
    strategy: AdjustmentStrategy = AdjustmentStrategy.RETRY_FAILED
    max_retries: int = 3

    def is_complete(self) -> bool:
        """Check if all legs have been filled"""
        return len(self.failed_legs) == 0

    def can_retry(self) -> bool:
        """Check if we can retry failed legs"""
        return self.retry_count < self.max_retries and len(self.failed_legs) > 0


@dataclass
class AdjustmentConfig:
    """Configuration for position adjustment logic"""
    default_strategy: AdjustmentStrategy = AdjustmentStrategy.RETRY_FAILED
    max_retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    allow_partial_positions: bool = True
    hedge_partial_fills: bool = False
    notify_on_partial: bool = True


class PositionAdjuster:
    """
    Handles position adjustments when spread orders have partial fills.

    When a multi-leg spread order has some legs filled and others fail, this
    class provides intelligent strategies to handle the situation:

    1. RETRY_FAILED: Retry failed legs with exponential backoff
    2. ROLLBACK_ALL: Reverse all successful legs (original behavior)
    3. KEEP_PARTIAL: Track successful legs as positions
    4. HEDGE_PARTIAL: Add protective hedge for unmatched legs
    """

    def __init__(self, execution_engine, config: Optional[AdjustmentConfig] = None):
        self.execution_engine = execution_engine
        self.config = config or AdjustmentConfig()

        # Track partial fill states
        self.partial_fills: Dict[str, PartialFillState] = {}

    async def handle_spread_result(
        self,
        result: SpreadExecutionResult,
        original_legs: List[Dict[str, Any]],
        spread_id: str,
        strategy: Optional[AdjustmentStrategy] = None
    ) -> SpreadExecutionResult:
        """
        Handle the result of a spread execution, applying adjustment logic if needed.

        Args:
            result: The result from execute_spread_order
            original_legs: The original leg definitions
            spread_id: Unique identifier for this spread order
            strategy: Override adjustment strategy for this order

        Returns:
            Final result after adjustments
        """
        # If spread fully succeeded, nothing to do
        if result.success:
            logger.info("Spread fully executed", spread_id=spread_id, legs=len(result.legs))
            return result

        # Identify failed legs
        executed_legs = [leg for leg in result.legs if leg.order.success]
        failed_leg_indices = [i for i, leg in enumerate(result.legs) if not leg.order.success]
        failed_legs = [original_legs[i] for i in failed_leg_indices]

        logger.warning(
            "Spread partially filled",
            spread_id=spread_id,
            executed=len(executed_legs),
            failed=len(failed_legs),
            failed_symbols=[leg.get("symbol") for leg in failed_legs]
        )

        # Create partial fill state
        state = PartialFillState(
            original_legs=original_legs,
            executed_legs=executed_legs,
            failed_legs=failed_legs,
            strategy=strategy or self.config.default_strategy,
            max_retries=self.config.max_retry_attempts
        )
        self.partial_fills[spread_id] = state

        # Apply adjustment strategy
        if state.strategy == AdjustmentStrategy.RETRY_FAILED:
            return await self._retry_failed_legs(spread_id, state)

        elif state.strategy == AdjustmentStrategy.ROLLBACK_ALL:
            return await self._rollback_all(spread_id, state)

        elif state.strategy == AdjustmentStrategy.KEEP_PARTIAL:
            return await self._keep_partial(spread_id, state)

        elif state.strategy == AdjustmentStrategy.HEDGE_PARTIAL:
            return await self._hedge_partial(spread_id, state)

        else:
            logger.error("Unknown adjustment strategy", strategy=state.strategy)
            return result

    async def _retry_failed_legs(
        self,
        spread_id: str,
        state: PartialFillState
    ) -> SpreadExecutionResult:
        """
        Retry failed legs with exponential backoff.

        This is the recommended strategy for handling partial fills in live trading.
        """
        while state.can_retry() and not state.is_complete():
            state.retry_count += 1
            delay = self.config.retry_delay_seconds * (2 ** (state.retry_count - 1))

            logger.info(
                "Retrying failed legs",
                spread_id=spread_id,
                attempt=state.retry_count,
                max_attempts=state.max_retries,
                delay_seconds=delay,
                failed_count=len(state.failed_legs)
            )

            await asyncio.sleep(delay)

            # Retry each failed leg
            newly_executed = []
            still_failed = []

            for leg in state.failed_legs:
                order = await self.execution_engine.place_order(
                    symbol=leg["symbol"],
                    side=leg["side"],
                    quantity=leg["quantity"],
                    product=leg.get("product", "NRML"),
                    order_type="MARKET",
                    price=None,
                    tag=f"{leg.get('tag', 'RETRY')}_{state.retry_count}",
                    use_limit_chase=leg.get("use_limit_chase", False)
                )

                leg_result = SpreadLegResult(
                    symbol=leg["symbol"],
                    side=leg["side"],
                    quantity=leg["quantity"],
                    product=leg.get("product", "NRML"),
                    tag=leg.get("tag", "RETRY"),
                    order=order
                )

                if order.success:
                    newly_executed.append(leg_result)
                    state.executed_legs.append(leg_result)
                    logger.info(
                        "Retry successful",
                        spread_id=spread_id,
                        symbol=leg["symbol"],
                        attempt=state.retry_count
                    )
                else:
                    still_failed.append(leg)
                    logger.warning(
                        "Retry failed",
                        spread_id=spread_id,
                        symbol=leg["symbol"],
                        reason=order.message,
                        attempt=state.retry_count
                    )

            # Update failed legs list
            state.failed_legs = still_failed

            # If all legs now executed, success!
            if state.is_complete():
                logger.info(
                    "Spread fully executed after retries",
                    spread_id=spread_id,
                    total_retries=state.retry_count
                )
                return SpreadExecutionResult(
                    success=True,
                    legs=state.executed_legs,
                    message=f"Spread completed after {state.retry_count} retries"
                )

        # Exhausted retries, decide what to do with partial fill
        if not state.is_complete():
            if self.config.allow_partial_positions:
                logger.warning(
                    "Keeping partial fill as positions",
                    spread_id=spread_id,
                    executed=len(state.executed_legs),
                    failed=len(state.failed_legs)
                )
                return SpreadExecutionResult(
                    success=False,
                    legs=state.executed_legs,
                    failed_leg_index=None,
                    message=f"Partial fill: {len(state.executed_legs)}/{len(state.original_legs)} legs executed"
                )
            else:
                # Rollback if partial positions not allowed
                logger.warning(
                    "Rolling back partial fill (partial positions not allowed)",
                    spread_id=spread_id
                )
                return await self._rollback_all(spread_id, state)

        return SpreadExecutionResult(
            success=True,
            legs=state.executed_legs,
            message=f"Spread completed after {state.retry_count} retries"
        )

    async def _rollback_all(
        self,
        spread_id: str,
        state: PartialFillState
    ) -> SpreadExecutionResult:
        """
        Rollback all successfully executed legs (original behavior).
        """
        logger.info(
            "Rolling back all executed legs",
            spread_id=spread_id,
            count=len(state.executed_legs)
        )

        rollback_results = []
        for leg in reversed(state.executed_legs):
            rollback_side = "SELL" if leg.side == "BUY" else "BUY"
            rollback_tag = f"{leg.tag}_ROLLBACK"

            try:
                order = await self.execution_engine.place_order(
                    symbol=leg.symbol,
                    side=rollback_side,
                    quantity=leg.quantity,
                    product=leg.product,
                    order_type="MARKET",
                    price=None,
                    tag=rollback_tag,
                    use_limit_chase=False
                )

                if order.success:
                    logger.info(
                        "Rollback successful",
                        spread_id=spread_id,
                        symbol=leg.symbol
                    )
                else:
                    logger.error(
                        "Rollback failed",
                        spread_id=spread_id,
                        symbol=leg.symbol,
                        reason=order.message
                    )

                rollback_results.append(order)

            except Exception as e:
                logger.error(
                    "Rollback exception",
                    spread_id=spread_id,
                    symbol=leg.symbol,
                    error=str(e),
                    exc_info=True
                )

        return SpreadExecutionResult(
            success=False,
            legs=state.executed_legs,
            failed_leg_index=None,
            message=f"Rolled back {len(state.executed_legs)} legs"
        )

    async def _keep_partial(
        self,
        spread_id: str,
        state: PartialFillState
    ) -> SpreadExecutionResult:
        """
        Keep successfully executed legs as positions.
        """
        logger.info(
            "Keeping partial fill as positions",
            spread_id=spread_id,
            executed=len(state.executed_legs),
            failed=len(state.failed_legs)
        )

        return SpreadExecutionResult(
            success=False,
            legs=state.executed_legs,
            failed_leg_index=None,
            message=f"Partial fill: {len(state.executed_legs)} legs executed, {len(state.failed_legs)} failed"
        )

    async def _hedge_partial(
        self,
        spread_id: str,
        state: PartialFillState
    ) -> SpreadExecutionResult:
        """
        Add protective hedge for unmatched legs.

        For example, if a debit spread has only the long leg filled,
        we might want to add a temporary hedge to reduce risk while
        we work on filling the short leg.
        """
        logger.info(
            "Adding hedge for partial fill",
            spread_id=spread_id,
            executed=len(state.executed_legs)
        )

        # TODO: Implement smart hedging logic based on position risk
        # For now, just keep the partial fill
        return await self._keep_partial(spread_id, state)

    def get_partial_fills(self) -> Dict[str, PartialFillState]:
        """Get all tracked partial fills"""
        return self.partial_fills

    def clear_partial_fill(self, spread_id: str) -> None:
        """Clear tracking for a completed spread"""
        if spread_id in self.partial_fills:
            del self.partial_fills[spread_id]
            logger.debug("Cleared partial fill tracking", spread_id=spread_id)
