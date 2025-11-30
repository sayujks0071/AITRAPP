"""
Allocation Veto - The Gatekeeper
=================================

Blocks capital allocation if safety checks fail.
Enforces "Performance Probation" to protect capital from underperforming strategies.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("aca_veto")


class AllocationVeto:
    """
    The Gatekeeper.
    
    Blocks capital allocation if safety checks fail.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Allocation Veto.
        
        Args:
            config: Configuration dictionary with veto parameters
        """
        self.max_drawdown_period = config.get("veto_max_drawdown", 5000.0)  # Rs
        self.min_win_rate = config.get("veto_min_win_rate", 0.35)
        self.probation_days = config.get("veto_probation_days", 3)
    
    def check(self, strategy_name: str, stats: Dict[str, Any]) -> List[str]:
        """
        Returns a list of veto reasons. Empty list = PASSED.
        
        Args:
            strategy_name: Name of the strategy
            stats: Dictionary with performance stats
                Example: {'pnl': float, 'win_rate': float, 'consecutive_losses': int, 'recent_pnl': float, 'trades': int}
        
        Returns:
            List of veto reasons (empty if passed)
        """
        reasons = []
        
        # 1. Drawdown Veto
        # If strategy lost > X amount recently
        recent_pnl = stats.get("recent_pnl", 0.0)
        if recent_pnl <= -self.max_drawdown_period:
            reasons.append(f"DRAWDOWN_BREACH: {recent_pnl} < -{self.max_drawdown_period}")
        
        # 2. Competence Veto
        # If win rate is statistically abysmal
        win_rate = stats.get("win_rate", 1.0)
        trades = stats.get("trades", 0)
        if trades > 10 and win_rate < self.min_win_rate:
            reasons.append(f"POOR_PERFORMANCE: WinRate {win_rate:.2f} < {self.min_win_rate}")
        
        # 3. Streak Veto (Tilt Protection)
        loss_streak = stats.get("consecutive_losses", 0)
        if loss_streak >= 4:
            reasons.append(f"TILT_PROTECTION: {loss_streak} consecutive losses")
        
        if reasons:
            logger.warning(f"🚫 VETO Applied to {strategy_name}: {', '.join(reasons)}")
        
        return reasons





