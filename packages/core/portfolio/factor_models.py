"""
Factor & Style Engine - Level 12
=================================

Analyzes Strategy Performance to determine Style Factors.
Tilts allocation towards the winning style (Momentum vs Carry).
"""

import logging
from typing import Dict, List

from packages.core.intelligence.sme import StrategicMemoryEngine

logger = logging.getLogger("pm_factors")


class FactorEngine:
    """
    Analyzes Strategy Performance to determine Style Factors.
    
    Tilts allocation towards the winning style (Momentum vs Carry).
    """
    
    def __init__(self, sme: StrategicMemoryEngine):
        """
        Initialize Factor Engine.
        
        Args:
            sme: Strategic Memory Engine instance
        """
        self.sme = sme
        
        # Map strategies to Factors
        self.style_map = {
            "TrendCreditSpreadV1": "MOMENTUM",
            "IntradayShortStrangleV1": "CARRY",
            "GammaScalper": "VOLATILITY",
            "OptionsRanker": "MEAN_REVERSION"
        }
    
    def get_factor_tilts(self, regime: str) -> Dict[str, float]:
        """
        Returns a weight modifier for each strategy based on its Factor Performance.
        
        e.g., {'TrendCreditSpreadV1': 1.2, 'IntradayShortStrangleV1': 0.8}
        
        Args:
            regime: Current market regime
        
        Returns:
            Dictionary mapping strategy names to tilt multipliers
        """
        # 1. Get Performance by Strategy
        # [('StrategyA', 0.65), ('StrategyB', 0.40)]
        performers = self.sme.query_best_strategies(regime)
        
        factor_scores = {
            "MOMENTUM": 0,
            "CARRY": 0,
            "VOLATILITY": 0,
            "MEAN_REVERSION": 0
        }
        
        # 2. Aggregate by Factor
        for strat_name, win_rate in performers:
            style = self.style_map.get(strat_name, "OTHER")
            if style in factor_scores:
                # Simple scoring: WinRate contributes to Factor Score
                factor_scores[style] += win_rate
        
        # 3. Determine Winners
        # If Momentum score > Carry score, tilt Momentum strategies up
        total_score = sum(factor_scores.values()) or 1
        
        tilts = {}
        logger.info(f"PME Factor Scores: {factor_scores}")
        
        for strat, style in self.style_map.items():
            if style not in factor_scores:
                tilts[strat] = 1.0
                continue
            
            # Relative strength of this factor vs average
            avg_score = total_score / len(factor_scores)
            if avg_score == 0:
                tilts[strat] = 1.0
            else:
                factor_strength = factor_scores[style] / avg_score
                # Dampen the tilt (e.g., max 1.5x boost, min 0.5x cut)
                tilt = max(0.5, min(factor_strength, 1.5))
                tilts[strat] = tilt
        
        return tilts
