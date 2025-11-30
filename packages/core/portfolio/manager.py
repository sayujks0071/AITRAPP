"""
Portfolio Management Engine (PME) - Level 12
============================================

Level 12: PM-Level Portfolio Engine.

Integrates Volatility Targeting + Factor Tilts + Risk Veto.
"""

import logging
from typing import Dict, List, Any

from packages.core.portfolio.risk_models import VolatilityTargeting
from packages.core.portfolio.factor_models import FactorEngine
from packages.core.allocation.veto import AllocationVeto
from packages.core.intelligence.sme import StrategicMemoryEngine

logger = logging.getLogger("pm_engine")


class PortfolioManager:
    """
    Level 12: PM-Level Portfolio Engine.
    
    Integrates Volatility Targeting + Factor Tilts + Risk Veto.
    """
    
    def __init__(
        self,
        risk_engine: Any,
        sme_engine: StrategicMemoryEngine,
        config: Dict[str, Any]
    ):
        """
        Initialize Portfolio Manager.
        
        Args:
            risk_engine: RiskManager instance
            sme_engine: Strategic Memory Engine instance
            config: Configuration dictionary
        """
        self.risk_engine = risk_engine
        self.config = config
        
        # Sub-Engines
        self.vol_target = VolatilityTargeting(
            target_vol_annual=config.get("target_vol", 0.15),
            max_leverage=config.get("max_leverage", 2.0)
        )
        self.factor_engine = FactorEngine(sme_engine)
        self.veto = AllocationVeto(config)
    
    def generate_allocation_vector(
        self,
        regime: str,
        account_nav: float,
        daily_returns_history: List[float]
    ) -> List[Dict]:
        """
        Generate allocation vector for strategies.
        
        Args:
            regime: Current market regime
            account_nav: Net Asset Value (account equity)
            daily_returns_history: List of daily returns (PnL / Equity)
        
        Returns:
            List of allocation dictionaries
        """
        logger.info(
            f"🏦 PME: Computing Allocation Vector (Regime: {regime}, NAV: {account_nav})"
        )
        
        # 1. Calculate Global Leverage Scalar (Vol Targeting)
        vol_scalar = self.vol_target.calculate_leverage_scalar(daily_returns_history)
        
        # 2. Calculate Factor Tilts (Alpha)
        # e.g., {'TrendStrat': 1.2, 'StrangleStrat': 0.8}
        tilts = self.factor_engine.get_factor_tilts(regime)
        
        # 3. Base Allocation (Equal Weight or Config)
        # In a real PM system, we'd optimize Mean-Variance here.
        # We'll start with Equal Weight for active strategies.
        # Assuming we know the strategy list (injected or config)
        strategy_list = list(tilts.keys())
        base_weight = 1.0 / len(strategy_list) if strategy_list else 0
        
        allocations = []
        
        for strat in strategy_list:
            # 4. Apply Logic
            
            # A. Veto Check
            # Need recent stats for veto (Mocking for structure)
            veto_reasons = self.veto.check(strat, {"recent_pnl": 0, "win_rate": 0.5})
            if veto_reasons:
                logger.info(f"PME: {strat} VETOED ({veto_reasons[0]})")
                allocations.append({"strategy_name": strat, "capital_pct": 0.0})
                continue
            
            # B. Apply Tilt & Scalar
            tilt_multiplier = tilts.get(strat, 1.0)
            
            # Formula: Weight = Base * FactorTilt * VolScalar
            final_weight = base_weight * tilt_multiplier * vol_scalar
            
            # C. Cap Constraints (e.g., Max 40% per strat)
            final_weight = min(
                final_weight,
                self.config.get("max_single_allocation", 0.40)
            )
            
            allocations.append({
                "strategy_name": strat,
                "capital_pct": round(final_weight, 4),
                "capital_value": round(final_weight * account_nav, 2),
                "reason": f"Tilt:{tilt_multiplier:.2f} * VolScale:{vol_scalar:.2f}"
            })
        
        self._log_portfolio_summary(allocations, account_nav)
        return allocations
    
    def _log_portfolio_summary(self, allocations: List[Dict], nav: float) -> None:
        """Log portfolio allocation summary."""
        total_exposure = sum(a['capital_pct'] for a in allocations)
        logger.info(f"PME: Total Gross Exposure: {total_exposure*100:.1f}% of NAV")
        for a in allocations:
            if a['capital_pct'] > 0:
                logger.info(
                    f"   > {a['strategy_name']}: ₹{a['capital_value']} "
                    f"({a['capital_pct']*100:.1f}%) [{a['reason']}]"
                )
