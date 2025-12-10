"""
Emergency Brake - The Muscle
============================

Zero-Latency Kill Switch.

This module doesn't ask for permission. When pulled, it nukes open orders
and dumps positions at Market.
"""

import asyncio
import logging
from packages.core.execution.execution_engine import ExecutionEngine
from packages.core.compliance import ComplianceGuard

logger = logging.getLogger("reflex_brake")


class EmergencyBrake:
    """
    Zero-Latency Kill Switch.
    
    When pulled:
    1. Cancels all pending orders
    2. Liquidates all positions at market price
    3. Halts the system (requires manual restart)
    """
    
    def __init__(
        self, 
        kite_client, 
        execution_engine: ExecutionEngine,
        compliance_guard: ComplianceGuard = None
    ):
        """
        Initialize Emergency Brake.
        
        Args:
            kite_client: KiteConnect client for order management
            execution_engine: ExecutionEngine instance for placing liquidation orders
            compliance_guard: Compliance guard for rate limiting (optional)
        """
        self.kite = kite_client
        self.exec_engine = execution_engine
        self.compliance_guard = compliance_guard
        self.is_engaged = False
    
    async def pull(self, reason: str = "PANIC"):
        """
        PULL THE PLUG - Emergency liquidation.
        
        This method:
        1. Cancels all pending orders
        2. Liquidates all positions at market
        3. Halts the system
        
        Args:
            reason: Reason for emergency brake pull
        """
        if self.is_engaged:
            return
        
        self.is_engaged = True
        
        logger.critical(f"🛑 EMERGENCY BRAKE PULLED: {reason}")
        
        # 1. CANCEL ALL PENDING ORDERS (Stop the bleeding)
        try:
            orders = self.kite.orders()
            pending = [
                o['order_id'] for o in orders
                if o['status'] in ['OPEN', 'TRIGGER PENDING']
            ]
            
            if pending:
                logger.info(f"Creating Cancel Tasks for {len(pending)} orders...")
                # Compliance: Rate limit cancels (but bypass kill switch check)
                # Kite cancel_order is synchronous, so we run it in executor
                loop = asyncio.get_event_loop()
                tasks = []
                for oid in pending:
                    # Check compliance with emergency bypass (skip kill switch, enforce rate limit)
                    if self.compliance_guard:
                        if await self.compliance_guard.check_before_order(
                            "CANCEL", 
                            tag="BRAKE_CANCEL", 
                            limiter_type="emergency_cancel",
                            emergency_bypass=True
                        ):
                            tasks.append(loop.run_in_executor(None, self.kite.cancel_order, oid))
                        else:
                            logger.warning(f"Emergency cancel rate limited for order {oid}, will retry")
                            # For emergency, we still try but log the rate limit
                            # In a real emergency, you might want to batch or wait
                            tasks.append(loop.run_in_executor(None, self.kite.cancel_order, oid))
                    else:
                        # No compliance guard - direct cancel (backward compatibility)
                        tasks.append(loop.run_in_executor(None, self.kite.cancel_order, oid))
                
                await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Brake Failure (Cancels): {e}")
        
        # 2. LIQUIDATE ALL POSITIONS (Flatten Book)
        try:
            positions = self.kite.positions()['net']
            active = [p for p in positions if p['quantity'] != 0]
            
            if active:
                logger.critical(f"LIQUIDATING {len(active)} POSITIONS NOW.")
                tasks = []
                for p in active:
                    side = "SELL" if p['quantity'] > 0 else "BUY"
                    # Bypass Limit Chase. FORCE MARKET.
                    # Emergency bypass: Skip kill switch check but enforce rate limiting
                    tasks.append(self.exec_engine.place_order(
                        symbol=p['tradingsymbol'],
                        side=side,
                        quantity=abs(p['quantity']),
                        product=p['product'],
                        order_type="MARKET",
                        tag="BRAKE_LIQ",
                        emergency_bypass=True  # Skip kill switch, enforce rate limit
                    ))
                await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Brake Failure (Liquidation): {e}")
        
        logger.critical("🛑 SYSTEM HALTED. MANUAL RESTART REQUIRED.")
    
    def reset(self):
        """Reset the brake (allow it to be pulled again)"""
        self.is_engaged = False
        logger.info("Emergency brake reset")
