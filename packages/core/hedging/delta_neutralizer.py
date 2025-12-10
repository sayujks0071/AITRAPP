"""Delta Neutralizer - Minimal Phase-1 Safety Version

Reads net delta from position store and uses NIFTY futures to neutralize.
Runs inside orchestrator scan loop with hard bounds.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import logging
import math

from packages.core.compliance import ComplianceGuard

logger = logging.getLogger(__name__)


@dataclass
class DeltaNeutralizerConfig:
    enabled: bool = True
    underlying: str = "NIFTY"
    fut_symbol: str = "NFO:NIFTY24NOVFUT"
    rebalance_threshold: float = 50.0
    max_hedge_lots: int = 2
    lot_size: int = 25


class DeltaNeutralizer:
    """
    Minimal Delta Neutralizer for Phase-1 safety.
    
    Features:
    - Reads net delta from position store
    - Uses NIFTY futures only to neutralize
    - Runs inside orchestrator scan loop with hard bounds
    - Does nothing unless net |Δ| > threshold
    - Never hedges more than max_hedge_lots
    """
    
    def __init__(
        self, 
        kite_client, 
        position_store, 
        cfg: DeltaNeutralizerConfig,
        compliance_guard: Optional[ComplianceGuard] = None
    ):
        self.kite = kite_client
        self.position_store = position_store
        self.cfg = cfg
        self.compliance_guard = compliance_guard
        
        logger.info(
            "[DeltaNeutralizer] Initialized",
            enabled=cfg.enabled,
            underlying=cfg.underlying,
            fut_symbol=cfg.fut_symbol,
            rebalance_threshold=cfg.rebalance_threshold,
            max_hedge_lots=cfg.max_hedge_lots,
            lot_size=cfg.lot_size,
            compliance_enabled=compliance_guard is not None
        )

    async def maybe_rebalance(self) -> None:
        """
        Check net delta and hedge if needed.
        
        Called periodically from orchestrator scan cycle.
        """
        if not self.cfg.enabled:
            return

        try:
            net_delta = self._compute_net_delta()
        except Exception as e:
            logger.error(f"[DeltaNeutralizer] Failed to compute net delta: {e}", exc_info=True)
            return

        if abs(net_delta) < self.cfg.rebalance_threshold:
            logger.debug(
                f"[DeltaNeutralizer] Net delta {net_delta:.2f} within threshold {self.cfg.rebalance_threshold}, no action"
            )
            return  # within band

        # Positive net_delta = synthetically long market → SELL futures
        # Negative net_delta = synthetically short → BUY futures
        fut_side = "SELL" if net_delta > 0 else "BUY"

        # how many futures lots to hedge?
        lots_needed = math.floor(abs(net_delta) / (self.cfg.lot_size * 1.0))
        lots_needed = max(1, min(lots_needed, self.cfg.max_hedge_lots))

        qty = lots_needed * self.cfg.lot_size

        logger.info(
            "[DeltaNeutralizer] Rebalancing: net_delta=%.2f, side=%s, lots=%d, qty=%d",
            net_delta, fut_side, lots_needed, qty,
        )

        # Compliance: Check kill switch and rate limit before placing order
        if self.compliance_guard:
            if not await self.compliance_guard.check_before_order("PLACE", tag="DELTA_HEDGE", limiter_type="delta_hedge"):
                logger.warning(
                    "[DeltaNeutralizer] Hedge order blocked by compliance guard",
                    net_delta=net_delta,
                    fut_side=fut_side,
                    qty=qty
                )
                return
        
        # VERY conservative: use MARKET for now, or you can wrap with LimitChase later
        try:
            # Try async place_order first
            if hasattr(self.kite, 'place_order'):
                import inspect
                if inspect.iscoroutinefunction(self.kite.place_order):
                    oid = await self.kite.place_order(
                        symbol=self.cfg.fut_symbol,
                        side=fut_side,
                        quantity=qty,
                        order_type="MARKET",
                        product="NRML",
                        tag="DELTA_HEDGE",
                    )
                else:
                    # Sync method
                    oid = self.kite.place_order(
                        exchange="NFO",
                        tradingsymbol=self.cfg.fut_symbol.split(":")[-1] if ":" in self.cfg.fut_symbol else self.cfg.fut_symbol,
                        transaction_type=fut_side,
                        quantity=qty,
                        order_type="MARKET",
                        product="NRML",
                        variety="regular",
                    )
                    # Kite returns dict with order_id
                    if isinstance(oid, dict):
                        oid = oid.get("order_id")
                
                logger.info("[DeltaNeutralizer] Hedge order placed: %s", oid)
            else:
                logger.warning("[DeltaNeutralizer] Kite client has no place_order method")
        except Exception as e:
            logger.error(f"[DeltaNeutralizer] Failed to place hedge order: {e}", exc_info=True)

    def _compute_net_delta(self) -> float:
        """
        Pulls open positions from position_store; expects each has 'delta' attribute
        or uses instrument greeks to compute approximate delta.
        """
        if not self.position_store:
            logger.warning("[DeltaNeutralizer] No position store available")
            return 0.0
        
        try:
            positions = self.position_store.get_open_positions()
        except Exception as e:
            logger.error(f"[DeltaNeutralizer] Failed to get open positions: {e}", exc_info=True)
            return 0.0
        
        net_delta = 0.0
        for pos in positions:
            # You likely already store greeks per leg; adapt as needed
            leg_delta = getattr(pos, "delta", None)
            if leg_delta is None:
                # fallback: approximate from option type / moneyness if needed
                # For now, skip positions without delta
                continue
            
            # Delta contribution = delta * quantity * side_multiplier
            # For LONG positions: +delta, for SHORT: -delta
            side_multiplier = 1.0 if getattr(pos, "side", "LONG") == "LONG" else -1.0
            quantity = getattr(pos, "quantity", 0)
            
            net_delta += leg_delta * quantity * side_multiplier
        
        return net_delta

