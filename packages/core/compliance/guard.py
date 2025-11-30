"""
Compliance Guard - Shared Rate Limiting & Kill Switch Enforcement
==================================================================

Provides a unified compliance guard that enforces:
1. Rate limiting (<10 OPS per SEBI requirements)
2. Kill switch checks (trading paused/killed)

All order paths (ExecutionEngine, DeltaNeutralizer, OCO, LimitChase) should
use this guard before calling broker APIs to ensure full compliance coverage.

Usage:
    guard = ComplianceGuard(rate_limiter, kill_switch_checker)
    
    # Before placing order
    if not await guard.check_before_order("PLACE", tag="STRATEGY"):
        return OrderResult(False, None, 0, 0.0, "BLOCKED", "Compliance check failed")
    
    # Place order...
    
    # Before modifying order
    if not await guard.check_before_order("MODIFY", tag="CHASE"):
        return False
    
    # Modify order...
    
    # Before canceling order
    if not await guard.check_before_order("CANCEL", tag="OCO"):
        return False
    
    # Cancel order...
"""

from typing import Optional, Callable
import logging
from packages.core.rate_limiter import LeakyBucketLimiter

logger = logging.getLogger(__name__)


class ComplianceGuard:
    """
    Unified compliance guard for all order operations.
    
    Enforces:
    - Rate limiting: <10 OPS (SEBI requirement)
    - Kill switch: Blocks if trading is paused/killed
    
    All broker API calls (place/modify/cancel) should go through this guard.
    """
    
    def __init__(
        self,
        rate_limiter: Optional[LeakyBucketLimiter] = None,
        kill_switch_checker: Optional[Callable[[], bool]] = None
    ):
        """
        Initialize compliance guard.
        
        Args:
            rate_limiter: Rate limiter instance (shared across all execution paths)
            kill_switch_checker: Callable that returns True if trading is paused/killed
        """
        self.rate_limiter = rate_limiter
        self._kill_switch_check = kill_switch_checker or (lambda: False)
        
        # Track blocked operations for metrics
        self._blocked_by_kill_switch = 0
        self._blocked_by_rate_limit = 0
        self._total_checks = 0
    
    async def check_before_order(
        self,
        operation: str,
        tag: str = "UNKNOWN",
        limiter_type: str = "order_operation",
        emergency_bypass: bool = False
    ) -> bool:
        """
        Check compliance before any order operation (place/modify/cancel).
        
        Args:
            operation: Operation type ("PLACE", "MODIFY", "CANCEL")
            tag: Order tag for logging
            limiter_type: Rate limiter type identifier
            emergency_bypass: If True, skip kill switch check (for emergency brake)
                            but still enforce rate limiting
            
        Returns:
            True if operation is allowed, False if blocked
        """
        self._total_checks += 1
        
        # 1. Kill switch check (highest priority, unless emergency bypass)
        if not emergency_bypass and self._kill_switch_check():
            self._blocked_by_kill_switch += 1
            logger.warning(
                f"[ComplianceGuard] {operation} blocked: Kill switch active",
                operation=operation,
                tag=tag
            )
            return False
        
        # 2. Rate limiting check (SEBI <10 OPS requirement)
        # Always enforce rate limiting, even in emergency (to avoid API rate limit errors)
        if self.rate_limiter:
            if not await self.rate_limiter.acquire(limiter_type=limiter_type):
                self._blocked_by_rate_limit += 1
                logger.warning(
                    f"[ComplianceGuard] {operation} rate limited: Exceeded 10 OPS threshold",
                    operation=operation,
                    tag=tag,
                    emergency_bypass=emergency_bypass
                )
                return False
        
        # All checks passed
        return True
    
    def get_stats(self) -> dict:
        """Get compliance guard statistics"""
        return {
            "total_checks": self._total_checks,
            "blocked_by_kill_switch": self._blocked_by_kill_switch,
            "blocked_by_rate_limit": self._blocked_by_rate_limit,
            "allowed": self._total_checks - self._blocked_by_kill_switch - self._blocked_by_rate_limit
        }

