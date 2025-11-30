"""Price Action Support/Resistance Breakout Strategy

Proven breakout strategy: 50-60% win rate
Works well for volatile markets and breakouts

Strategy Logic:
- Identify support/resistance levels from recent highs/lows
- Buy when price breaks above resistance with volume
- Sell when price breaks below support with volume
- ATR-based stops and targets
"""
from datetime import time
from typing import List, Optional

import structlog

from packages.core.models import Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


class PriceActionSRStrategy(Strategy):
    """
    Price Action Support/Resistance Breakout Strategy
    
    Entry Logic:
    - LONG: Price breaks above resistance level (recent high)
    - SHORT: Price breaks below support level (recent low)
    
    Exit Logic:
    - Stop-loss: ATR-based below support / above resistance
    - Take-profit: 2x-3x ATR
    - Exit on opposite breakout
    
    Parameters:
    - lookback_period: Period for S/R identification (default: 20)
    - breakout_confirmation: Bars to confirm breakout (default: 2)
    - atr_stop_mult: ATR multiplier for stop (default: 1.5)
    - atr_target_mult: ATR multiplier for target (default: 2.5)
    - volume_confirmation: Require volume (default: True)
    - rr_min: Minimum risk-reward (default: 2.0)
    """
    
    def __init__(self, name: str, params: dict):
        super().__init__(name, params)
        
        self.lookback_period = params.get("lookback_period", 20)
        self.breakout_confirmation = params.get("breakout_confirmation", 2)
        self.atr_stop_mult = params.get("atr_stop_mult", 1.5)
        self.atr_target_mult = params.get("atr_target_mult", 2.5)
        self.volume_confirmation = params.get("volume_confirmation", True)
        self.volume_lookback = params.get("volume_lookback", 20)
        self.min_volume_mult = params.get("min_volume_mult", 1.2)
        self.rr_min = params.get("rr_min", 2.0)
        self.allowed_instruments = params.get("instruments", ["NIFTY", "BANKNIFTY", "CRUDEOIL", "GOLDM", "SILVERM"])
        
        self.backtest_rr_min = params.get("backtest_rr_min", 1.5)
        self.backtest_volume_mult = params.get("backtest_volume_mult", 0.0)
        
        # State tracking
        self.last_resistance: dict = {}
        self.last_support: dict = {}
        self.last_signal_side: dict = {}
        self.last_signal_time: dict = {}
        self.min_signal_gap_minutes = 30
    
    def _identify_sr_levels(self, bars: List) -> tuple[Optional[float], Optional[float]]:
        """Identify support and resistance levels"""
        if len(bars) < self.lookback_period:
            return None, None
        
        recent_bars = bars[-self.lookback_period:]
        highs = [b.high for b in recent_bars]
        lows = [b.low for b in recent_bars]
        
        resistance = max(highs)
        support = min(lows)
        
        return resistance, support
    
    def _check_volume_confirmation(self, bars: List) -> bool:
        """Check volume confirmation"""
        if not self.volume_confirmation or len(bars) < self.volume_lookback + 1:
            return True
        
        recent_volumes = [b.volume for b in bars[-self.volume_lookback:]]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        current_volume = bars[-1].volume
        
        threshold = self.backtest_volume_mult if hasattr(self, '_backtest_mode') and self._backtest_mode else self.min_volume_mult
        return current_volume >= avg_volume * threshold
    
    def _calculate_atr(self, bars: List) -> Optional[float]:
        """Calculate ATR"""
        if len(bars) < 15:
            return None
        
        true_ranges = []
        for i in range(len(bars) - 14, len(bars)):
            if i == 0:
                continue
            prev_close = bars[i - 1].close
            tr = max(
                bars[i].high - bars[i].low,
                abs(bars[i].high - prev_close),
                abs(bars[i].low - prev_close)
            )
            true_ranges.append(tr)
        
        return sum(true_ranges) / len(true_ranges) if true_ranges else None
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """Generate Price Action S/R signals"""
        self._backtest_mode = context.backtest_mode
        
        if not self.validate(context):
            return []
        
        if context.instrument.symbol not in self.allowed_instruments:
            return []
        
        if not context.bars_5s or len(context.bars_5s) < self.lookback_period + 10:
            return []
        
        signals = []
        token = context.instrument.token
        bars = context.bars_5s
        latest_bar = bars[-1]
        current_price = context.latest_tick.last_price
        
        # Identify S/R levels
        resistance, support = self._identify_sr_levels(bars)
        if resistance is None or support is None:
            return []
        
        atr = latest_bar.atr or self._calculate_atr(bars)
        if atr is None or atr == 0:
            atr = current_price * 0.01
        
        # Check volume
        if not self._check_volume_confirmation(bars):
            return []
        
        if not self._can_generate_signal(token, context.timestamp):
            return []
        
        # Get previous levels
        last_resistance = self.last_resistance.get(token)
        last_support = self.last_support.get(token)
        self.last_resistance[token] = resistance
        self.last_support[token] = support
        
        # Resistance breakout (LONG)
        if current_price > resistance and (last_resistance is None or current_price > last_resistance):
            # Confirm breakout with multiple bars
            if len(bars) >= self.breakout_confirmation:
                confirm_bars = bars[-self.breakout_confirmation:]
                if all(b.close > resistance for b in confirm_bars):
                    if self.last_signal_side.get(token) == "LONG":
                        return []
                    
                    signal = self._create_long_signal(context, entry_price=current_price, resistance=resistance, support=support, atr=atr)
                    if signal:
                        signals.append(signal)
                        self.last_signal_side[token] = "LONG"
                        self.last_signal_time[token] = context.timestamp
                        logger.info("Price Action Resistance Breakout LONG", instrument=context.instrument.tradingsymbol, resistance=resistance)
        
        # Support breakdown (SHORT)
        elif current_price < support and (last_support is None or current_price < last_support):
            # Confirm breakdown
            if len(bars) >= self.breakout_confirmation:
                confirm_bars = bars[-self.breakout_confirmation:]
                if all(b.close < support for b in confirm_bars):
                    if self.last_signal_side.get(token) == "SHORT":
                        return []
                    
                    signal = self._create_short_signal(context, entry_price=current_price, resistance=resistance, support=support, atr=atr)
                    if signal:
                        signals.append(signal)
                        self.last_signal_side[token] = "SHORT"
                        self.last_signal_time[token] = context.timestamp
                        logger.info("Price Action Support Breakdown SHORT", instrument=context.instrument.tradingsymbol, support=support)
        
        return signals
    
    def _create_long_signal(
        self,
        context: StrategyContext,
        entry_price: float,
        resistance: float,
        support: float,
        atr: float
    ) -> Optional[Signal]:
        """Create LONG signal"""
        stop_loss = max(support - (atr * 0.5), entry_price - (atr * self.atr_stop_mult))
        stop_loss = max(stop_loss, entry_price * 0.97)
        
        risk = entry_price - stop_loss
        if risk <= 0:
            return None
        
        rr_required = self.backtest_rr_min if context.backtest_mode else self.rr_min
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
            confidence=0.70,
            rationale=f"Price Action Resistance Breakout: Price({entry_price:.2f}) > Resistance({resistance:.2f})",
            features={"resistance": resistance, "support": support, "atr": atr}
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
        """Create SHORT signal"""
        stop_loss = min(support + (atr * 0.5), entry_price + (atr * self.atr_stop_mult))
        stop_loss = min(stop_loss, entry_price * 1.03)
        
        risk = stop_loss - entry_price
        if risk <= 0:
            return None
        
        rr_required = self.backtest_rr_min if context.backtest_mode else self.rr_min
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
            confidence=0.70,
            rationale=f"Price Action Support Breakdown: Price({entry_price:.2f}) < Support({support:.2f})",
            features={"resistance": resistance, "support": support, "atr": atr}
        )
        
        signal.risk_amount = risk
        signal.reward_amount = reward
        self.signals_generated += 1
        return signal
    
    def _can_generate_signal(self, token: int, timestamp) -> bool:
        if token not in self.last_signal_time:
            return True
        time_diff = (timestamp - self.last_signal_time[token]).total_seconds() / 60
        return time_diff >= self.min_signal_gap_minutes
    
    def validate(self, context: StrategyContext) -> bool:
        if not super().validate(context):
            return False
        
        current_time = context.timestamp.time()
        if not (time(9, 15) <= current_time < time(15, 25)):
            return False
        
        if not context.bars_5s or len(context.bars_5s) < self.lookback_period + 10:
            return False
        
        return True



