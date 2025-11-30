"""
Portfolio Risk Models - Level 12
=================================

Volatility Targeting and Risk Modeling for the Portfolio Management Engine.

Implements Modern Portfolio Theory (MPT) adapted for high-frequency trading.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("pm_risk")


class VolatilityTargeting:
    """
    Implements Volatility Targeting to size positions dynamically.
    
    Formula: Exposure = (Target_Vol / Realized_Vol) * Equity
    
    If markets are quiet, it increases size. If markets are wild, it scales down
    to keep risk constant.
    """
    
    def __init__(self, target_vol_annual: float = 0.15, max_leverage: float = 2.0):
        """
        Initialize Volatility Targeting.
        
        Args:
            target_vol_annual: Target annualized volatility (default: 15%)
            max_leverage: Maximum leverage multiplier (default: 2.0x)
        """
        self.target_vol = target_vol_annual
        self.max_leverage = max_leverage
        # 252 trading days, sqrt(252) ~ 15.87
        self.annualization_factor = 15.87
    
    def calculate_leverage_scalar(self, daily_returns: List[float]) -> float:
        """
        Returns a multiplier (0.0 to max_leverage).
        
        Args:
            daily_returns: List of daily returns (PnL / Equity)
        
        Returns:
            Leverage scalar (e.g., 1.5x means increase size by 50%)
        """
        if len(daily_returns) < 20:
            logger.warning("PME: Not enough data for Vol Targeting. Defaulting to 1.0x")
            return 1.0
        
        # Calculate rolling realized volatility (annualized)
        returns_std = np.std(daily_returns)
        realized_vol = returns_std * self.annualization_factor
        
        if realized_vol == 0:
            return 1.0
        
        # The Magic Formula
        scalar = self.target_vol / realized_vol
        
        # Cap leverage for safety
        final_scalar = min(scalar, self.max_leverage)
        
        logger.info(
            f"PME: RealizedVol: {realized_vol:.1%}, Target: {self.target_vol:.1%}, "
            f"Scalar: {final_scalar:.2f}x"
        )
        return final_scalar


class CovarianceEngine:
    """
    Calculates correlations between strategies to prevent over-concentration.
    
    Uses covariance matrix to ensure diversification.
    """
    
    def calculate_diversification_score(self, strategy_returns: Dict[str, List[float]]) -> float:
        """
        Calculate diversification score based on strategy correlations.
        
        Args:
            strategy_returns: Dictionary mapping strategy names to lists of returns
        
        Returns:
            Score from 0.0 to 1.0 (1.0 = Uncorrelated/Good, 0.0 = Perfectly Correlated/Bad)
        """
        if not strategy_returns or len(strategy_returns) < 2:
            return 1.0  # Can't calculate correlation with < 2 strategies
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(strategy_returns)
            
            # Calculate correlation matrix
            corr_matrix = df.corr()
            
            # Average absolute correlation (excluding diagonal)
            mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
            avg_corr = corr_matrix.where(mask).abs().mean().mean()
            
            # Convert to diversification score (lower correlation = higher score)
            diversification_score = 1.0 - avg_corr
            
            logger.debug(
                f"PME: Diversification score: {diversification_score:.2f} "
                f"(avg correlation: {avg_corr:.2f})"
            )
            
            return max(0.0, min(1.0, diversification_score))
        except Exception as e:
            logger.warning(f"PME: Error calculating diversification: {e}")
            return 1.0  # Default to good diversification on error
    
    def calculate_portfolio_volatility(
        self,
        strategy_weights: Dict[str, float],
        strategy_returns: Dict[str, List[float]]
    ) -> float:
        """
        Calculate portfolio-level volatility using covariance matrix.
        
        Args:
            strategy_weights: Dictionary mapping strategy names to weights
            strategy_returns: Dictionary mapping strategy names to lists of returns
        
        Returns:
            Portfolio volatility (annualized)
        """
        if not strategy_weights or not strategy_returns:
            return 0.0
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(strategy_returns)
            
            # Calculate covariance matrix
            cov_matrix = df.cov() * 252  # Annualize
            
            # Create weight vector
            strategies = list(strategy_weights.keys())
            weights = np.array([strategy_weights[s] for s in strategies if s in df.columns])
            
            if len(weights) == 0:
                return 0.0
            
            # Portfolio variance = w^T * Cov * w
            portfolio_variance = np.dot(weights, np.dot(cov_matrix.loc[strategies, strategies], weights))
            
            # Portfolio volatility = sqrt(variance)
            portfolio_vol = np.sqrt(portfolio_variance)
            
            logger.debug(f"PME: Portfolio volatility: {portfolio_vol:.1%}")
            
            return portfolio_vol
        except Exception as e:
            logger.warning(f"PME: Error calculating portfolio volatility: {e}")
            return 0.0





