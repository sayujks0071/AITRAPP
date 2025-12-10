"""
Simplified test strategies to validate backtest engine functionality.

These strategies are designed to generate signals with minimal requirements,
helping us validate that the backtest engine is working correctly.
"""
import structlog
from datetime import datetime
from typing import List, Dict, Any, Optional
from packages.core.strategies.base import Strategy, StrategyContext
from packages.core.models import Signal, SignalSide, Instrument

logger = structlog.get_logger(__name__)


class AlwaysSignalStrategy(Strategy):
    """
    Test strategy that ALWAYS generates a signal if basic data is available.
    
    Purpose: Validate that backtest engine can generate and execute signals.
    This strategy bypasses all filters to test core functionality.
    """
    
    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)
        self.signal_count = 0
        self.max_signals = params.get("max_signals", 10)  # Limit signals for testing
        logger.info(f"AlwaysSignalStrategy initialized (max_signals={self.max_signals})")
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """Always generate a signal if basic data exists"""
        if not self.validate(context):
            return []
        
        # Check if we've hit the limit
        if self.signal_count >= self.max_signals:
            return []
        
        # Only generate for NIFTY/BANKNIFTY
        if context.instrument.symbol not in ["NIFTY", "BANKNIFTY"]:
            return []
        
        # Check for basic data
        if not context.latest_tick:
            logger.debug("No latest_tick available")
            return []
        
        entry_price = context.latest_tick.last_price
        if entry_price <= 0:
            logger.debug(f"Invalid entry price: {entry_price}")
            return []
        
        # Generate a simple LONG signal
        signal = Signal(
            strategy_name=self.name,
            instrument=context.instrument,
            side=SignalSide.LONG,
            entry_price=entry_price,
            stop_loss=entry_price * 0.98,  # 2% stop
            take_profit_1=entry_price * 1.03,  # 3% target
            confidence=0.5,  # Low confidence (test signal)
            timestamp=context.timestamp,
            features={"test_signal": True, "signal_number": self.signal_count + 1}
        )
        
        self.signal_count += 1
        logger.info(
            f"AlwaysSignalStrategy: Generated test signal #{self.signal_count}",
            instrument=context.instrument.tradingsymbol,
            entry=entry_price,
            stop=signal.stop_loss,
            target=signal.take_profit_1
        )
        
        return [signal]
    
    def validate(self, context: StrategyContext) -> bool:
        """Always allow to run for testing"""
        return True


class PriceMovementStrategy(Strategy):
    """
    Test strategy that generates signals based on simple price movement.
    
    Purpose: Validate that strategies can use bar data and price movements.
    """
    
    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)
        self.min_price_change_pct = params.get("min_price_change_pct", 0.5)  # 0.5% movement
        self.last_signal_time: Optional[datetime] = None
        self.signal_interval_minutes = params.get("signal_interval_minutes", 30)
        logger.info(f"PriceMovementStrategy initialized (min_change={self.min_price_change_pct}%)")
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """Generate signal if price moved enough"""
        if not self.validate(context):
            return []
        
        # Only generate for NIFTY/BANKNIFTY
        if context.instrument.symbol not in ["NIFTY", "BANKNIFTY"]:
            return []
        
        # Check for basic data
        if not context.latest_tick:
            return []
        
        # Check cooldown
        if self.last_signal_time:
            time_diff = (context.timestamp - self.last_signal_time).total_seconds() / 60
            if time_diff < self.signal_interval_minutes:
                return []
        
        # Check for bar data
        if not context.bars_5s or len(context.bars_5s) < 2:
            logger.debug("Insufficient bar data")
            return []
        
        # Calculate price change
        current_price = context.latest_tick.last_price
        previous_bar = context.bars_5s[-2]
        previous_price = previous_bar.close
        
        if previous_price <= 0:
            return []
        
        price_change_pct = ((current_price - previous_price) / previous_price) * 100
        
        # Generate signal if price moved enough
        if abs(price_change_pct) >= self.min_price_change_pct:
            side = SignalSide.LONG if price_change_pct > 0 else SignalSide.SHORT
            
            signal = Signal(
                strategy_name=self.name,
                instrument=context.instrument,
                side=side,
                entry_price=current_price,
                stop_loss=current_price * (0.98 if side == SignalSide.LONG else 1.02),
                take_profit_1=current_price * (1.03 if side == SignalSide.LONG else 0.97),
                confidence=0.6,
                timestamp=context.timestamp,
                features={
                    "price_change_pct": price_change_pct,
                    "bars_used": len(context.bars_5s)
                }
            )
            
            self.last_signal_time = context.timestamp
            logger.info(
                f"PriceMovementStrategy: Generated signal",
                instrument=context.instrument.tradingsymbol,
                side=side.value,
                price_change_pct=price_change_pct,
                entry=current_price
            )
            
            return [signal]
        
        return []
    
    def validate(self, context: StrategyContext) -> bool:
        """Always allow to run for testing"""
        return True
