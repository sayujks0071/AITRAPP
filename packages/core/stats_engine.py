"""Statistics engine for tracking strategy performance"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class StrategyStats:
    """Performance statistics for a strategy"""
    hit_rate: float  # wins / trades
    expectancy_perc: float  # avg PnL per trade (% of risk)
    max_drawdown_perc: float  # max drawdown %
    recent_loss_streak: int  # consecutive losses
    num_trades_window: int  # number of trades in window
    total_pnl: float  # total PnL in window
    avg_win: float  # average win
    avg_loss: float  # average loss


class StatsEngine:
    """
    Tracks and computes performance statistics for strategies.
    
    Uses PositionStore as canonical source for trade/PnL data.
    """
    
    def __init__(
        self,
        strategies: Optional[Dict[str, Any]] = None,
        position_store: Optional[Any] = None
    ):
        self.strategies = strategies or {}
        self.position_store = position_store
        # In production, would have database connection
        self._trade_cache: Dict[str, List[Dict[str, Any]]] = {}
    
    def get_stats(
        self,
        strategy_name: str,
        trade_window: int = 50,
        day_window: int = 30
    ) -> StrategyStats:
        """
        Get performance statistics for a strategy.
        
        Args:
            strategy_name: Name of the strategy
            trade_window: Number of recent trades to consider
            day_window: Number of recent days to consider
        
        Returns:
            StrategyStats object
        """
        # Try to get stats from position store (canonical source)
        if self.position_store and hasattr(self.position_store, 'get_strategy_stats'):
            stats_dict = self.position_store.get_strategy_stats(strategy_name, trade_window, day_window)
            return StrategyStats(
                hit_rate=stats_dict.get("hit_rate", 0.5),
                expectancy_perc=stats_dict.get("expectancy_perc", 0.0),
                max_drawdown_perc=stats_dict.get("max_drawdown_perc", 0.0),
                recent_loss_streak=stats_dict.get("recent_loss_streak", 0),
                num_trades_window=stats_dict.get("num_trades_window", 0),
                total_pnl=stats_dict.get("total_pnl", 0.0),
                avg_win=stats_dict.get("avg_win", 0.0),
                avg_loss=stats_dict.get("avg_loss", 0.0),
            )
        
        # Fallback: get stats from strategy instance
        strategy = self.strategies.get(strategy_name)
        if strategy:
            return self._get_stats_from_strategy(strategy, trade_window, day_window)
        
        # Final fallback: default stats
        return self._get_default_stats()
    
    def _get_stats_from_strategy(
        self,
        strategy: Any,
        trade_window: int,
        day_window: int
    ) -> StrategyStats:
        """Extract stats from strategy instance"""
        try:
            # Get win rate from strategy
            win_rate = getattr(strategy, 'win_rate', 0.0) / 100.0  # Convert from %
            win_count = getattr(strategy, 'win_count', 0)
            loss_count = getattr(strategy, 'loss_count', 0)
            total_trades = win_count + loss_count
            
            # Calculate hit rate
            hit_rate = win_rate if total_trades > 0 else 0.0
            
            # Get total PnL
            total_pnl = getattr(strategy, 'total_pnl', 0.0)
            
            # Estimate expectancy (simplified)
            # In production, would calculate from actual trade PnL
            if total_trades > 0:
                expectancy_perc = (total_pnl / total_trades) / 100.0  # Rough estimate
            else:
                expectancy_perc = 0.0
            
            # Estimate drawdown (simplified)
            # In production, would track peak equity and calculate properly
            max_drawdown_perc = 0.0  # Placeholder
            
            # Estimate loss streak (simplified)
            recent_loss_streak = 0  # Placeholder
            
            # Limit to window
            num_trades_window = min(total_trades, trade_window)
            
            # Estimate avg win/loss
            avg_win = total_pnl / win_count if win_count > 0 else 0.0
            avg_loss = total_pnl / loss_count if loss_count > 0 else 0.0
            
            return StrategyStats(
                hit_rate=hit_rate,
                expectancy_perc=expectancy_perc,
                max_drawdown_perc=max_drawdown_perc,
                recent_loss_streak=recent_loss_streak,
                num_trades_window=num_trades_window,
                total_pnl=total_pnl,
                avg_win=avg_win,
                avg_loss=avg_loss,
            )
        except Exception as e:
            logger.error("Error getting stats from strategy", strategy=strategy, error=str(e))
            return self._get_default_stats()
    
    def _get_default_stats(self) -> StrategyStats:
        """Return default stats when no data available"""
        return StrategyStats(
            hit_rate=0.5,  # Neutral
            expectancy_perc=0.0,
            max_drawdown_perc=0.0,
            recent_loss_streak=0,
            num_trades_window=0,
            total_pnl=0.0,
            avg_win=0.0,
            avg_loss=0.0,
        )
