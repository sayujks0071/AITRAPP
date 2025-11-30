"""
Autonomous Capital Allocator (ACA) - Level 9
============================================

Level 9: Dynamic Capital Rebalancing Engine.

Flow: Regime -> SME Lookup -> Scoring -> Veto -> Normalization -> Allocation.

While HiveMind (Level 7) *proposes* allocations, the ACA *calculates and enforces* them.
"""

import logging
import math
from typing import Dict, List, Any, Optional

from packages.core.allocation.veto import AllocationVeto
from packages.core.intelligence.sme import StrategicMemoryEngine

logger = logging.getLogger("aca_allocator")


class AutonomousCapitalAllocator:
    """
    Level 9: Dynamic Capital Rebalancing Engine.
    
    Flow: Regime -> SME Lookup -> Scoring -> Veto -> Normalization -> Allocation.
    """
    
    def __init__(
        self,
        risk_engine,
        sme_engine: StrategicMemoryEngine,
        config: Dict[str, Any]
    ):
        """
        Initialize Autonomous Capital Allocator.
        
        Args:
            risk_engine: RiskManager instance
            sme_engine: Strategic Memory Engine instance
            config: Configuration dictionary
        """
        self.risk_engine = risk_engine
        self.sme = sme_engine
        self.config = config
        
        self.veto = AllocationVeto(config)
        
        # Limits
        self.global_cap_limit = config.get("global_capital_limit", 0.80)  # Max 80% deployment
        self.min_allocation = config.get("min_allocation_pct", 0.05)
        self.max_allocation = config.get("max_allocation_pct", 0.40)
    
    def run_allocation_cycle(
        self,
        current_regime: str,
        event_ctx: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Calculates new capital caps for all strategies based on the current regime.
        
        Args:
            current_regime: Current market regime (e.g., "HIGH_VOL", "LOW_MEAN_REVERT")
            event_ctx: Optional event context (e.g., {"is_event_day": True})
        
        Returns:
            List of allocation dictionaries with strategy_name, capital_pct, and reason
        """
        logger.info(f"💰 ACA: Starting Allocation Cycle. Regime: {current_regime}")
        
        # 1. Fetch Candidates from SME (Who performs here?)
        # Returns list of (StrategyName, WinRate)
        candidates = self.sme.query_best_strategies(current_regime)
        
        if not candidates:
            logger.warning("ACA: No historical data for this regime. Defaulting to equal weights.")
            return self._fallback_equal_weight()
        
        # 2. Score Candidates (Performance Score)
        scored_strats = {}
        for name, win_rate in candidates:
            # Fetch deeper stats if available in SME, simplified here
            # Score = WinRate^2 (emphasize high probability)
            score = win_rate ** 2
            scored_strats[name] = score
        
        # 3. Apply Veto (Risk Filter)
        active_strats = {}
        total_score = 0.0
        
        for name, score in scored_strats.items():
            # Get recent stats for Veto Check (Mocking fetching from Risk Engine/SME)
            # In prod: recent_stats = self.sme.get_recent_stats(name)
            recent_stats = {"recent_pnl": 0, "win_rate": 0.5, "trades": 5}
            
            reasons = self.veto.check(name, recent_stats)
            if not reasons:
                active_strats[name] = score
                total_score += score
            else:
                # Strategy Vetoed -> 0 Capital
                logger.info(f"ACA: {name} Zeroed out (Veto).")
        
        # 4. Normalize & Constrain (The Math)
        allocations = []
        
        # Event Dampener: If Event Day, reduce global cap by 50%
        dampener = 0.5 if (event_ctx and event_ctx.get("is_event_day")) else 1.0
        effective_global_limit = self.global_cap_limit * dampener
        
        for name, score in active_strats.items():
            # Raw % of the "pie"
            raw_pct = score / total_score if total_score > 0 else 0
            
            # Apply Constraints
            # 1. Scale by global limit
            scaled_pct = raw_pct * effective_global_limit
            
            # 2. Clamp to Min/Max
            final_pct = max(self.min_allocation, min(scaled_pct, self.max_allocation))
            
            allocations.append({
                "strategy_name": name,
                "capital_pct": round(final_pct, 3),
                "reason": f"Regime Score: {score:.2f}"
            })
        
        # Log result
        for alloc in allocations:
            logger.info(
                f"   -> {alloc['strategy_name']}: {alloc['capital_pct']*100}% ({alloc['reason']})"
            )
        
        return allocations
    
    def _fallback_equal_weight(self) -> List[Dict[str, Any]]:
        """
        If we have no memory, give Trend and Strangle 20% each (Safety default).
        
        Returns:
            List of default allocation dictionaries
        """
        return [
            {
                "strategy_name": "TrendCreditSpreadV1",
                "capital_pct": 0.20,
                "reason": "Fallback: Equal weight (no SME data)"
            },
            {
                "strategy_name": "IntradayShortStrangleV1",
                "capital_pct": 0.20,
                "reason": "Fallback: Equal weight (no SME data)"
            }
        ]
