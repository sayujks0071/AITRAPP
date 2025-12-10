"""Breakout Strategy for Indian Markets (Nifty)

Based on top 10 Nifty trading strategies.
Support/Resistance Breakout strategy.

Strategy Logic:
- Buy when price breaks above resistance level
- Sell when price breaks below support level
- Use ATR for stop-loss and targets
- Volume confirmation required
"""
from datetime import time
from typing import List, Optional

import structlog

from packages.core.models import Bar, Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


class BreakoutStrategy(Strategy):
    """
    Breakout Strategy (Support/Resistance)
    
    Logic:
    1. Identify support and resistance levels (recent highs/lows)
    2. Buy when price breaks above resistance (breakout)
    3. Sell when price breaks below support (breakdown)
    4. Use ATR for stop-loss and targets
    5. Volume confirmation required
    
    Parameters:
    - lookback_period: Period to identify support/resistance (default: 20)
    - breakout_confirmation_bars: Bars to confirm breakout (default: 2)
    - atr_period: ATR period (default: 14)
    - atr_stop_mult: ATR multiplier for stop-loss (default: 1.5)
    - atr_target_mult: ATR multiplier for target (default: 2.5)
    - volume_confirmation: Require volume above average (default: True)
    - volume_lookback: Period for volume average (default: 20)
    - min_volume_mult: Minimum volume multiplier (default: 1.5)
    - rr_min: Minimum risk-reward ratio (default: 2.0)
    - max_positions: Maximum concurrent positions (default: 2)
    - instruments: List of instruments to trade (default: ["NIFTY", "BANKNIFTY"])
    """
    
    def __init__(self, name: str, params: dict):
        super().__init__(name, params)
        
        self.lookback_period = params.get("lookback_period", 20)
        self.breakout_confirmation_bars = params.get("breakout_confirmation_bars", 2)
        self.atr_period = params.get("atr_period", 14)
        self.atr_stop_mult = params.get("atr_stop_mult", 1.5)
        self.atr_target_mult = params.get("atr_target_mult", 2.5)
        self.volume_confirmation = params.get("volume_confirmation", True)
        self.volume_lookback = params.get("volume_lookback", 20)
        self.min_volume_mult = params.get("min_volume_mult", 1.5)
        self.rr_min = params.get("rr_min", 2.0)
        
        # Backtest mode parameters (relaxed filters)
        self.backtest_rr_min = params.get("backtest_rr_min", 1.0)
        self.backtest_volume_mult = params.get("backtest_volume_mult", 0.0)
        self.allowed_instruments = params.get("instruments", ["NIFTY", "BANKNIFTY"])
        
        # State tracking
        self.resistance_levels: dict = {}  # token -> resistance level
        self.support_levels: dict = {}  # token -> support level
        self.last_signal_side: dict = {}
        self.last_signal_time: dict = {}
        self.min_signal_gap_minutes = 30  # Longer cooldown for breakouts
    
    def _calculate_atr(self, bars: List[Bar], period: int) -> Optional[float]:
        """Calculate Average True Range"""
        if len(bars) < period + 1:
            return None
        
        true_ranges = []
        for i in range(len(bars) - period, len(bars)):
            if i == 0:
                continue
            prev_close = bars[i - 1].close
            high = bars[i].high
            low = bars[i].low
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        if not true_ranges:
            return None
        
        return sum(true_ranges) / len(true_ranges)
    
    def _identify_levels(self, bars: List[Bar]) -> tuple[Optional[float], Optional[float]]:
        """Identify support and resistance levels"""
        if len(bars) < self.lookback_period:
            return None, None
        
        recent_bars = bars[-self.lookback_period:]
        highs = [b.high for b in recent_bars]
        lows = [b.low for b in recent_bars]
        
        resistance = max(highs)
        support = min(lows)
        
        return resistance, support
    
    def _check_volume_confirmation(self, bars: List[Bar]) -> bool:
        """Check if volume is above average"""
        if not self.volume_confirmation or len(bars) < self.volume_lookback + 1:
            return True
        
        recent_volumes = [b.volume for b in bars[-self.volume_lookback:]]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        current_volume = bars[-1].volume
        
        return current_volume >= avg_volume * self.min_volume_mult
    
    def _check_volume_confirmation_backtest(self, bars: List[Bar]) -> bool:
        """Relaxed volume check for backtesting"""
        if not self.volume_confirmation or len(bars) < self.volume_lookback + 1:
            return True
        
        recent_volumes = [b.volume for b in bars[-self.volume_lookback:]]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        current_volume = bars[-1].volume
        
        return current_volume >= avg_volume * self.backtest_volume_mult
    
    def _confirm_breakout(self, bars: List[Bar], level: float, direction: str) -> bool:
        """Confirm breakout with multiple bars"""
        if len(bars) < self.breakout_confirmation_bars:
            return False
        
        recent_bars = bars[-self.breakout_confirmation_bars:]
        
        if direction == "UP":
            # All recent bars should be above resistance
            return all(b.close > level for b in recent_bars)
        else:  # DOWN
            # All recent bars should be below support
            return all(b.close < level for b in recent_bars)
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """Generate breakout signals"""
        # Store backtest mode for use in signal creation
        self._backtest_mode = context.backtest_mode
        
        if not self.validate(context):
            return []
        
        if context.instrument.symbol not in self.allowed_instruments:
            return []
        
        min_bars = max(self.lookback_period, self.atr_period) + 10
        if not context.bars_5s or len(context.bars_5s) < min_bars:
            return []
        
        signals = []
        token = context.instrument.token
        bars = context.bars_5s
        current_price = context.latest_tick.last_price
        
        # Identify support and resistance
        resistance, support = self._identify_levels(bars)
        
        if resistance is None or support is None:
            return []
        
        # Update levels
        self.resistance_levels[token] = resistance
        self.support_levels[token] = support
        
        # Calculate ATR
        atr = self._calculate_atr(bars, self.atr_period)
        if atr is None or atr == 0:
            atr = current_price * 0.01
        
        # Check volume confirmation (relaxed in backtest mode)
        if context.backtest_mode:
            if not self._check_volume_confirmation_backtest(bars):
                logger.debug("Volume confirmation failed (backtest)", token=token)
                return []
        else:
            if not self._check_volume_confirmation(bars):
                logger.debug("Volume confirmation failed", token=token)
                return []
        
        # Check for cooldown (relaxed in backtest mode)
        if context.backtest_mode:
            if token in self.last_signal_time:
                time_diff = (context.timestamp - self.last_signal_time[token]).total_seconds() / 60
                if time_diff < 5:  # 5 min cooldown in backtest
                    logger.debug("Cooldown period active (backtest)", token=token)
                    return []
        else:
            if not self._can_generate_signal(token, context.timestamp):
                logger.debug("Cooldown period active", token=token)
                return []
        
        # Check for resistance breakout (LONG)
        if current_price > resistance:
            if not self._confirm_breakout(bars, resistance, "UP"):
                logger.debug("Breakout confirmation failed", token=token)
                return []
            
            if self.last_signal_side.get(token) == "LONG":
                logger.debug("Duplicate LONG signal prevented (breakout)", token=token)
                return []
            
            logger.debug(
                "Creating LONG signal (resistance breakout)",
                token=token,
                price=current_price,
                resistance=resistance,
                atr=atr
            )
            
            signal = self._create_long_signal(
                context,
                entry_price=current_price,
                resistance=resistance,
                support=support,
                atr=atr
            )
            
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "LONG"
                self.last_signal_time[token] = context.timestamp
                logger.info(
                    "Breakout LONG signal (above resistance)",
                    instrument=context.instrument.tradingsymbol,
                    entry=signal.entry_price,
                    resistance=resistance
                )
        
        # Check for support breakdown (SHORT)
        elif current_price < support:
            if not self._confirm_breakout(bars, support, "DOWN"):
                logger.debug("Breakdown confirmation failed", token=token)
                return []
            
            if self.last_signal_side.get(token) == "SHORT":
                logger.debug("Duplicate SHORT signal prevented (breakdown)", token=token)
                return []
            
            logger.debug(
                "Creating SHORT signal (support breakdown)",
                token=token,
                price=current_price,
                support=support,
                atr=atr
            )
            
            signal = self._create_short_signal(
                context,
                entry_price=current_price,
                resistance=resistance,
                support=support,
                atr=atr
            )
            
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "SHORT"
                self.last_signal_time[token] = context.timestamp
                logger.info(
                    "Breakdown SHORT signal (below support)",
                    instrument=context.instrument.tradingsymbol,
                    entry=signal.entry_price,
                    support=support
                )
        
        return signals
    
    def _create_long_signal(
        self,
        context: StrategyContext,
        entry_price: float,
        resistance: float,
        support: float,
        atr: float
    ) -> Optional[Signal]:
        """Create LONG signal (resistance breakout)"""
        # Stop-loss below resistance (failed breakout)
        stop_loss = resistance - (atr * self.atr_stop_mult)
        stop_loss = max(stop_loss, entry_price * 0.97)
        
        risk = entry_price - stop_loss
        if risk <= 0:
            return None
        
        # Target based on ATR (momentum target)
        rr_required = self.backtest_rr_min if hasattr(self, '_backtest_mode') and self._backtest_mode else self.rr_min
        reward = risk * rr_required
        take_profit_1 = entry_price + (reward * 0.6)
        take_profit_2 = entry_price + reward
        
        signal = Signal(
            strategy_name=self.name,
            timestamp=context.timestamp,
            instrument=context.instrument,
            side=SignalSide.LONG,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            confidence=0.75,
            rationale=f"Breakout LONG: Price {entry_price:.2f} broke above resistance {resistance:.2f}",
            features={
                "resistance": resistance,
                "support": support,
                "atr": atr,
                "breakout_type": "RESISTANCE_BREAKOUT"
            }
        )
        
        signal.risk_amount = risk
        signal.reward_amount = reward
        
        self.signals_generated += 1
        
        return signal
    
    def _create_short_signal(
        self,
        context: StrategyContext,
        entry_price: float,
        resistance: float,
        support: float,
        atr: float
    ) -> Optional[Signal]:
        """Create SHORT signal (support breakdown)"""
        # Stop-loss above support (failed breakdown)
        stop_loss = support + (atr * self.atr_stop_mult)
        stop_loss = min(stop_loss, entry_price * 1.03)
        
        risk = stop_loss - entry_price
        if risk <= 0:
            return None
        
        # Target based on ATR (momentum target)
        rr_required = self.backtest_rr_min if hasattr(self, '_backtest_mode') and self._backtest_mode else self.rr_min
        reward = risk * rr_required
        take_profit_1 = entry_price - (reward * 0.6)
        take_profit_2 = entry_price - reward
        
        signal = Signal(
            strategy_name=self.name,
            timestamp=context.timestamp,
            instrument=context.instrument,
            side=SignalSide.SHORT,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            confidence=0.75,
            rationale=f"Breakdown SHORT: Price {entry_price:.2f} broke below support {support:.2f}",
            features={
                "resistance": resistance,
                "support": support,
                "atr": atr,
                "breakout_type": "SUPPORT_BREAKDOWN"
            }
        )
        
        signal.risk_amount = risk
        signal.reward_amount = reward
        
        self.signals_generated += 1
        
        return signal
    
    def _can_generate_signal(self, token: int, timestamp) -> bool:
        """Check if enough time has passed since last signal"""
        if token not in self.last_signal_time:
            return True
        
        time_diff = (timestamp - self.last_signal_time[token]).total_seconds() / 60
        
        return time_diff >= self.min_signal_gap_minutes
    
    def validate(self, context: StrategyContext) -> bool:
        """Validate breakout strategy can run"""
        if not super().validate(context):
            return False
        
        current_time = context.timestamp.time()
        market_open = time(9, 15)
        market_close = time(15, 25)
        
        if not (market_open <= current_time < market_close):
            return False
        
        min_bars = max(self.lookback_period, self.atr_period) + 10
        if not context.bars_5s or len(context.bars_5s) < min_bars:
            return False
        
        return True

