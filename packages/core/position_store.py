"""Position and PnL store - Canonical source for position tracking and PnL calculation"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from packages.core.models import Position, Instrument, SignalSide, PositionStatus

logger = structlog.get_logger(__name__)


@dataclass
class StrategyExposure:
    """Exposure summary for a strategy"""
    strategy_name: str
    total_notional: float
    short_premium_notional: float
    long_premium_notional: float
    net_vega: float  # Net vega exposure
    net_delta: float  # Net delta exposure
    num_positions: int
    unrealized_pnl: float
    realized_pnl: float


class PositionStore:
    """
    Canonical position and PnL store.
    
    Provides unified interface for:
    - Position tracking
    - PnL calculation
    - Notional aggregation
    - Strategy exposure calculation
    """
    
    def __init__(self):
        # In-memory position store (in production, would use database)
        self.positions: Dict[str, Position] = {}  # position_id -> Position
        self.strategy_positions: Dict[str, List[str]] = {}  # strategy_name -> [position_ids]
        self.underlying_positions: Dict[str, List[str]] = {}  # underlying -> [position_ids]
        
        # PnL tracking
        self.realized_pnl_by_strategy: Dict[str, float] = {}  # strategy_name -> cumulative realized PnL
        self.trades_by_strategy: Dict[str, List[Dict[str, Any]]] = {}  # strategy_name -> [trade records]
        
        logger.info("PositionStore initialized")
    
    def add_position(self, position: Position) -> None:
        """Add a new position to the store"""
        self.positions[position.position_id] = position
        
        # Index by strategy
        if position.strategy_name not in self.strategy_positions:
            self.strategy_positions[position.strategy_name] = []
        self.strategy_positions[position.strategy_name].append(position.position_id)
        
        # Index by underlying
        underlying = position.instrument.symbol
        if underlying not in self.underlying_positions:
            self.underlying_positions[underlying] = []
        self.underlying_positions[underlying].append(position.position_id)
        
        logger.debug(
            "Position added",
            position_id=position.position_id,
            strategy=position.strategy_name,
            underlying=underlying
        )
    
    def update_position(self, position_id: str, current_price: float) -> None:
        """Update position with current price and recalculate PnL"""
        if position_id not in self.positions:
            return
        
        position = self.positions[position_id]
        position.current_price = current_price
        position.update_pnl()
    
    def close_position(self, position_id: str, exit_price: float, exit_time: datetime) -> None:
        """Close a position and record realized PnL"""
        if position_id not in self.positions:
            return
        
        position = self.positions[position_id]
        position.close_price = exit_price
        position.close_time = exit_time
        position.status = PositionStatus.CLOSED
        
        # Calculate realized PnL
        if position.side == SignalSide.LONG:
            realized_pnl = (exit_price - position.entry_price) * position.quantity
        else:
            realized_pnl = (position.entry_price - exit_price) * position.quantity
        
        position.realized_pnl = realized_pnl
        
        # Track by strategy
        strategy_name = position.strategy_name
        if strategy_name not in self.realized_pnl_by_strategy:
            self.realized_pnl_by_strategy[strategy_name] = 0.0
        self.realized_pnl_by_strategy[strategy_name] += realized_pnl
        
        # Track trade record
        if strategy_name not in self.trades_by_strategy:
            self.trades_by_strategy[strategy_name] = []
        
        self.trades_by_strategy[strategy_name].append({
            "position_id": position_id,
            "entry_time": position.entry_time,
            "exit_time": exit_time,
            "entry_price": position.entry_price,
            "exit_price": exit_price,
            "quantity": position.quantity,
            "side": position.side,
            "pnl": realized_pnl,
            "pnl_pct": (realized_pnl / (position.entry_price * position.quantity)) * 100.0 if position.entry_price > 0 else 0.0,
        })
        
        logger.info(
            "Position closed",
            position_id=position_id,
            strategy=strategy_name,
            pnl=realized_pnl
        )
    
    def get_open_positions(self, strategy_name: Optional[str] = None, underlying: Optional[str] = None) -> List[Position]:
        """Get open positions, optionally filtered by strategy or underlying"""
        positions = []
        for pos in self.positions.values():
            if not pos.is_open:
                continue
            if strategy_name and pos.strategy_name != strategy_name:
                continue
            if underlying and pos.instrument.symbol != underlying:
                continue
            positions.append(pos)
        return positions
    
    def aggregate_short_premium_notional(
        self,
        strategies: set,
        underlying: Optional[str] = None
    ) -> float:
        """
        Aggregate short premium notional across specified strategies.
        
        Args:
            strategies: Set of strategy names to include
            underlying: Optional underlying filter
        
        Returns:
            Total short premium notional
        """
        total = 0.0
        
        for strategy_name in strategies:
            position_ids = self.strategy_positions.get(strategy_name, [])
            for pos_id in position_ids:
                position = self.positions.get(pos_id)
                if not position or not position.is_open:
                    continue
                
                if underlying and position.instrument.symbol != underlying:
                    continue
                
                # For short positions, notional = entry_price * quantity
                if position.side == SignalSide.SHORT:
                    notional = position.entry_price * position.quantity
                    total += notional
        
        return total
    
    def aggregate_tail_hedge_notional(
        self,
        underlying: str,
        tail_type: str = "DEEP_OTM_PUT"
    ) -> float:
        """
        Aggregate tail hedge notional (deep OTM puts).
        
        Args:
            underlying: Underlying symbol
            tail_type: Type of tail hedge (currently "DEEP_OTM_PUT")
        
        Returns:
            Total tail hedge notional
        """
        total = 0.0
        
        position_ids = self.underlying_positions.get(underlying, [])
        for pos_id in position_ids:
            position = self.positions.get(pos_id)
            if not position or not position.is_open:
                continue
            
            # Check if this is a tail hedge
            # In production, would check position tags or strategy name
            is_tail = (
                position.instrument.is_option
                and position.instrument.instrument_type.name == "PE"  # Put
                and position.side == SignalSide.LONG
                and (position.strategy_name == "TailShortVolOverlay" or
                     getattr(position, 'is_tail_hedge', False))
            )
            
            if is_tail:
                # For long positions, notional = current_price * quantity
                notional = position.current_price * position.quantity
                total += notional
        
        return total
    
    def get_strategy_exposure(self, strategy_name: str) -> StrategyExposure:
        """Get exposure summary for a strategy"""
        position_ids = self.strategy_positions.get(strategy_name, [])
        
        total_notional = 0.0
        short_premium_notional = 0.0
        long_premium_notional = 0.0
        net_vega = 0.0  # Would calculate from Greeks in production
        net_delta = 0.0  # Would calculate from Greeks in production
        num_positions = 0
        unrealized_pnl = 0.0
        
        for pos_id in position_ids:
            position = self.positions.get(pos_id)
            if not position or not position.is_open:
                continue
            
            num_positions += 1
            notional = position.entry_price * position.quantity
            
            if position.side == SignalSide.SHORT:
                short_premium_notional += notional
            else:
                long_premium_notional += notional
            
            total_notional += notional
            unrealized_pnl += position.unrealized_pnl
        
        realized_pnl = self.realized_pnl_by_strategy.get(strategy_name, 0.0)
        
        return StrategyExposure(
            strategy_name=strategy_name,
            total_notional=total_notional,
            short_premium_notional=short_premium_notional,
            long_premium_notional=long_premium_notional,
            net_vega=net_vega,
            net_delta=net_delta,
            num_positions=num_positions,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
        )
    
    def book_pnl_for_strategy(
        self,
        strategy_name: str,
        book_type: str = "gamma_scalper"
    ) -> float:
        """
        Calculate book PnL for a strategy (e.g. gamma scalper, calendar arb).
        
        Args:
            strategy_name: Strategy name
            book_type: Type of book ("gamma_scalper", "calendar_arb", "dispersion_pair")
        
        Returns:
            Total book PnL (unrealized + realized)
        """
        exposure = self.get_strategy_exposure(strategy_name)
        return exposure.unrealized_pnl + exposure.realized_pnl
    
    def capital_used_for_strategy(
        self,
        strategy_name: str,
        book_type: str = "gamma_scalper"
    ) -> float:
        """
        Calculate capital used for a strategy book.
        
        Args:
            strategy_name: Strategy name
            book_type: Type of book
        
        Returns:
            Total capital used (notional or margin)
        """
        exposure = self.get_strategy_exposure(strategy_name)
        # For now, use total notional as proxy for capital used
        # In production, would calculate actual margin/notional
        return exposure.total_notional
    
    def get_strategy_stats(
        self,
        strategy_name: str,
        trade_window: int = 50,
        day_window: int = 30
    ) -> Dict[str, Any]:
        """
        Get performance statistics for a strategy.
        
        Args:
            strategy_name: Strategy name
            trade_window: Number of recent trades to consider
            day_window: Number of recent days to consider
        
        Returns:
            Dict with stats (hit_rate, expectancy, drawdown, etc.)
        """
        trades = self.trades_by_strategy.get(strategy_name, [])
        
        if not trades:
            return {
                "hit_rate": 0.5,
                "expectancy_perc": 0.0,
                "max_drawdown_perc": 0.0,
                "recent_loss_streak": 0,
                "num_trades_window": 0,
                "total_pnl": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
            }
        
        # Filter by window (simplified - would use actual dates in production)
        recent_trades = trades[-trade_window:] if len(trades) > trade_window else trades
        
        if not recent_trades:
            return {
                "hit_rate": 0.5,
                "expectancy_perc": 0.0,
                "max_drawdown_perc": 0.0,
                "recent_loss_streak": 0,
                "num_trades_window": 0,
                "total_pnl": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
            }
        
        # Calculate stats
        wins = [t for t in recent_trades if t["pnl"] > 0]
        losses = [t for t in recent_trades if t["pnl"] <= 0]
        
        hit_rate = len(wins) / len(recent_trades) if recent_trades else 0.0
        
        # Expectancy (avg PnL per trade as % of risk)
        # Simplified: use avg PnL % as proxy
        avg_pnl_pct = sum(t["pnl_pct"] for t in recent_trades) / len(recent_trades) if recent_trades else 0.0
        expectancy_perc = avg_pnl_pct / 100.0  # Convert to decimal
        
        # Max drawdown (simplified - would track peak equity in production)
        pnls = [t["pnl"] for t in recent_trades]
        cumulative_pnl = 0.0
        peak = 0.0
        max_dd = 0.0
        
        for pnl in pnls:
            cumulative_pnl += pnl
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            drawdown = peak - cumulative_pnl
            if drawdown > max_dd:
                max_dd = drawdown
        
        # Calculate drawdown as % (would need initial capital)
        max_drawdown_perc = (max_dd / 10000.0) if max_dd > 0 else 0.0  # Placeholder
        
        # Recent loss streak
        recent_loss_streak = 0
        for t in reversed(recent_trades):
            if t["pnl"] <= 0:
                recent_loss_streak += 1
            else:
                break
        
        # Calculate total PnL, avg win, avg loss
        total_pnl = sum(t["pnl"] for t in recent_trades)
        avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0.0
        avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0.0
        
        return {
            "hit_rate": hit_rate,
            "expectancy_perc": expectancy_perc,
            "max_drawdown_perc": max_drawdown_perc,
            "recent_loss_streak": recent_loss_streak,
            "num_trades_window": len(recent_trades),
            "total_pnl": total_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
        }


