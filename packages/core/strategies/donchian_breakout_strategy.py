"""Donchian Channel Breakout Strategy - Turtle Trading System

Famous momentum strategy with proven track record
Based on Richard Dennis' Turtle Trading system

Strategy Logic:
- Buy when price breaks above Donchian upper channel (20-period high)
- Sell when price breaks below Donchian lower channel (20-period low)
- ATR-based position sizing and stops
- Volume confirmation for breakouts
"""
from datetime import time
from typing import List, Optional

import structlog

from packages.core.models import Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


class DonchianBreakoutStrategy(Strategy):
    """
    Donchian Channel Breakout Strategy (Turtle Trading)
    
    Entry Logic:
    - LONG: Price breaks above 20-period high (upper channel)
    - SHORT: Price breaks below 20-period low (lower channel)
    
    Exit Logic:
    - Stop-loss: Opposite channel (entry channel - 2*ATR for long, entry channel + 2*ATR for short)
    - Take-profit: 2x-3x ATR from entry
    - Trailing stop: Donchian channel itself
    
    Parameters:
    - donchian_period: Period for Donchian channel (default: 20)
    - atr_period: ATR period (default: 14)
    - atr_stop_mult: ATR multiplier for stop-loss (default: 2.0)
    - atr_target_mult: ATR multiplier for target (default: 3.0)
    - volume_confirmation: Require volume above average (default: True)
    - min_volume_mult: Minimum volume multiplier (default: 1.2)
    - rr_min: Minimum risk-reward ratio (default: 2.0)
    """
    
    def __init__(self, name: str, params: dict):
        super().__init__(name, params)
        
        self.donchian_period = params.get("donchian_period", 20)
        self.atr_period = params.get("atr_period", 14)
        self.atr_stop_mult = params.get("atr_stop_mult", 2.0)
        self.atr_target_mult = params.get("atr_target_mult", 3.0)
        self.volume_confirmation = params.get("volume_confirmation", True)
        self.volume_lookback = params.get("volume_lookback", 20)
        self.min_volume_mult = params.get("min_volume_mult", 1.2)
        self.rr_min = params.get("rr_min", 2.0)
        self.allowed_instruments = params.get("instruments", ["NIFTY", "BANKNIFTY", "CRUDEOIL", "GOLDM", "SILVERM"])
        
        # Backtest mode
        self.backtest_rr_min = params.get("backtest_rr_min", 1.5)
        self.backtest_volume_mult = params.get("backtest_volume_mult", 0.0)
        
        # State tracking
        self.last_upper: dict = {}  # token -> last upper channel
        self.last_lower: dict = {}  # token -> last lower channel
        self.last_signal_side: dict = {}
        self.last_signal_time: dict = {}
        self.min_signal_gap_minutes = 30
    
    def _calculate_atr(self, bars: List) -> Optional[float]:
        """Calculate Average True Range"""
        if len(bars) < self.atr_period + 1:
            return None
        
        true_ranges = []
        for i in range(len(bars) - self.atr_period, len(bars)):
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
    
    def _check_volume_confirmation(self, bars: List) -> bool:
        """Check if volume is above average"""
        if not self.volume_confirmation or len(bars) < self.volume_lookback + 1:
            return True
        
        recent_volumes = [b.volume for b in bars[-self.volume_lookback:]]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        current_volume = bars[-1].volume
        
        return current_volume >= avg_volume * self.min_volume_mult
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """Generate Donchian breakout signals"""
        if not self.validate(context):
            return []
        
        if context.instrument.symbol not in self.allowed_instruments:
            return []
        
        min_bars = max(self.donchian_period, self.atr_period) + 10
        if not context.bars_5s or len(context.bars_5s) < min_bars:
            return []
        
        signals = []
        token = context.instrument.token
        bars = context.bars_5s
        latest_bar = bars[-1]
        current_price = context.latest_tick.last_price
        
        # Get Donchian channels (from indicators if available, else calculate)
        dc_upper = latest_bar.dc_upper if hasattr(latest_bar, 'dc_upper') else None
        dc_lower = latest_bar.dc_lower if hasattr(latest_bar, 'dc_lower') else None
        
        # Fallback: calculate from bars
        if dc_upper is None or dc_lower is None:
            if len(bars) >= self.donchian_period:
                highs = [b.high for b in bars[-self.donchian_period:]]
                lows = [b.low for b in bars[-self.donchian_period:]]
                dc_upper = max(highs)
                dc_lower = min(lows)
            else:
                return []
        
        atr = latest_bar.atr or self._calculate_atr(bars)
        if atr is None or atr == 0:
            atr = current_price * 0.01
        
        # Check volume confirmation
        if not context.backtest_mode:
            if not self._check_volume_confirmation(bars):
                return []
        
        # Check cooldown
        if not self._can_generate_signal(token, context.timestamp):
            return []
        
        # Detect breakouts
        last_upper = self.last_upper.get(token)
        last_lower = self.last_lower.get(token)
        self.last_upper[token] = dc_upper
        self.last_lower[token] = dc_lower
        
        # Upper channel breakout (LONG)
        if last_upper is not None and current_price > dc_upper and (not last_upper or current_price > last_upper):
            # Price broke above upper channel
            if self.last_signal_side.get(token) == "LONG":
                return []
            
            signal = self._create_long_signal(context, entry_price=current_price, upper_channel=dc_upper, atr=atr)
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "LONG"
                self.last_signal_time[token] = context.timestamp
                logger.info(
                    "Donchian Upper Breakout LONG signal",
                    instrument=context.instrument.tradingsymbol,
                    entry=signal.entry_price,
                    upper_channel=dc_upper
                )
        
        # Lower channel breakdown (SHORT)
        elif last_lower is not None and current_price < dc_lower and (not last_lower or current_price < last_lower):
            # Price broke below lower channel
            if self.last_signal_side.get(token) == "SHORT":
                return []
            
            signal = self._create_short_signal(context, entry_price=current_price, lower_channel=dc_lower, atr=atr)
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "SHORT"
                self.last_signal_time[token] = context.timestamp
                logger.info(
                    "Donchian Lower Breakdown SHORT signal",
                    instrument=context.instrument.tradingsymbol,
                    entry=signal.entry_price,
                    lower_channel=dc_lower
                )
        
        return signals
    
    def _create_long_signal(
        self,
        context: StrategyContext,
        entry_price: float,
        upper_channel: float,
        atr: float
    ) -> Optional[Signal]:
        """Create LONG signal on upper breakout"""
        # Stop-loss: Below lower channel by ATR buffer
        stop_loss = upper_channel - (atr * self.atr_stop_mult)
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
            confidence=0.75,
            rationale=f"Donchian Upper Breakout: Price({entry_price:.2f}) > Upper({upper_channel:.2f})",
            features={
                "upper_channel": upper_channel,
                "atr": atr,
                "breakout_type": "UPPER"
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
        lower_channel: float,
        atr: float
    ) -> Optional[Signal]:
        """Create SHORT signal on lower breakdown"""
        # Stop-loss: Above upper channel by ATR buffer
        stop_loss = lower_channel + (atr * self.atr_stop_mult)
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
            confidence=0.75,
            rationale=f"Donchian Lower Breakdown: Price({entry_price:.2f}) < Lower({lower_channel:.2f})",
            features={
                "lower_channel": lower_channel,
                "atr": atr,
                "breakout_type": "LOWER"
            }
        )
        
        signal.risk_amount = risk
        signal.reward_amount = reward
        self.signals_generated += 1
        
        return signal
    
    def _can_generate_signal(self, token: int, timestamp) -> bool:
        """Check cooldown period"""
        if token not in self.last_signal_time:
            return True
        time_diff = (timestamp - self.last_signal_time[token]).total_seconds() / 60
        return time_diff >= self.min_signal_gap_minutes
    
    def validate(self, context: StrategyContext) -> bool:
        """Validate Donchian strategy"""
        if not super().validate(context):
            return False
        
        current_time = context.timestamp.time()
        market_open = time(9, 15)
        market_close = time(15, 25)
        
        if not (market_open <= current_time < market_close):
            return False
        
        min_bars = max(self.donchian_period, self.atr_period) + 10
        if not context.bars_5s or len(context.bars_5s) < min_bars:
            return False
        
        return True



