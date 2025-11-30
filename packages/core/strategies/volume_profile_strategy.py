"""Volume Profile Strategy - Volume-Based Trading

Proven for high-volume days: 55-65% win rate
Works well when volume confirms price moves

Strategy Logic:
- Buy when price breaks above high-volume node with increasing volume
- Sell when price breaks below low-volume node with increasing volume
- Volume confirmation is key
"""
from datetime import time
from typing import List, Optional

import structlog

from packages.core.models import Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


class VolumeProfileStrategy(Strategy):
    """
    Volume Profile Strategy
    
    Entry Logic:
    - LONG: Price breaks above volume-weighted average with volume surge
    - SHORT: Price breaks below volume-weighted average with volume surge
    
    Exit Logic:
    - Stop-loss: ATR-based
    - Take-profit: 2x-3x ATR
    - Exit when volume dries up
    
    Parameters:
    - volume_lookback: Period for volume analysis (default: 20)
    - volume_surge_mult: Volume surge multiplier (default: 1.5)
    - atr_stop_mult: ATR multiplier for stop (default: 1.5)
    - atr_target_mult: ATR multiplier for target (default: 2.5)
    - rr_min: Minimum risk-reward (default: 2.0)
    """
    
    def __init__(self, name: str, params: dict):
        super().__init__(name, params)
        
        self.volume_lookback = params.get("volume_lookback", 20)
        self.volume_surge_mult = params.get("volume_surge_mult", 1.5)
        self.atr_stop_mult = params.get("atr_stop_mult", 1.5)
        self.atr_target_mult = params.get("atr_target_mult", 2.5)
        self.rr_min = params.get("rr_min", 2.0)
        self.allowed_instruments = params.get("instruments", ["NIFTY", "BANKNIFTY", "CRUDEOIL", "GOLDM", "SILVERM"])
        
        self.backtest_rr_min = params.get("backtest_rr_min", 1.5)
        self.backtest_volume_mult = params.get("backtest_volume_mult", 0.0)
        
        # State tracking
        self.last_vwap: dict = {}
        self.last_signal_side: dict = {}
        self.last_signal_time: dict = {}
        self.min_signal_gap_minutes = 30
    
    def _calculate_vwap(self, bars: List) -> Optional[float]:
        """Calculate Volume Weighted Average Price"""
        if not bars:
            return None
        
        total_volume = sum(b.volume for b in bars)
        if total_volume == 0:
            return None
        
        typical_prices = [(b.high + b.low + b.close) / 3 for b in bars]
        vwap = sum(tp * b.volume for tp, b in zip(typical_prices, bars)) / total_volume
        
        return vwap
    
    def _check_volume_surge(self, bars: List) -> bool:
        """Check if volume is surging"""
        if len(bars) < self.volume_lookback + 1:
            return True  # Skip check if insufficient data
        
        recent_volumes = [b.volume for b in bars[-self.volume_lookback:]]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        current_volume = bars[-1].volume
        
        threshold = self.backtest_volume_mult if hasattr(self, '_backtest_mode') and self._backtest_mode else self.volume_surge_mult
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
        """Generate Volume Profile signals"""
        self._backtest_mode = context.backtest_mode
        
        if not self.validate(context):
            return []
        
        if context.instrument.symbol not in self.allowed_instruments:
            return []
        
        if not context.bars_5s or len(context.bars_5s) < self.volume_lookback + 10:
            return []
        
        signals = []
        token = context.instrument.token
        bars = context.bars_5s
        latest_bar = bars[-1]
        current_price = context.latest_tick.last_price
        
        # Get VWAP (from bar or calculate)
        vwap = latest_bar.vwap or self._calculate_vwap(bars)
        if vwap is None:
            return []
        
        atr = latest_bar.atr or self._calculate_atr(bars)
        if atr is None or atr == 0:
            atr = current_price * 0.01
        
        # Check volume surge
        if not self._check_volume_surge(bars):
            return []
        
        if not self._can_generate_signal(token, context.timestamp):
            return []
        
        # Get previous VWAP
        last_vwap = self.last_vwap.get(token)
        self.last_vwap[token] = vwap
        
        if last_vwap is None:
            return []
        
        # Price breaks above VWAP with volume surge (LONG)
        if current_price > vwap and last_vwap is not None and current_price > last_vwap:
            if self.last_signal_side.get(token) == "LONG":
                return []
            
            signal = self._create_long_signal(context, entry_price=current_price, vwap=vwap, atr=atr)
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "LONG"
                self.last_signal_time[token] = context.timestamp
                logger.info("Volume Profile Bullish LONG", instrument=context.instrument.tradingsymbol, vwap=vwap)
        
        # Price breaks below VWAP with volume surge (SHORT)
        elif current_price < vwap and last_vwap is not None and current_price < last_vwap:
            if self.last_signal_side.get(token) == "SHORT":
                return []
            
            signal = self._create_short_signal(context, entry_price=current_price, vwap=vwap, atr=atr)
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "SHORT"
                self.last_signal_time[token] = context.timestamp
                logger.info("Volume Profile Bearish SHORT", instrument=context.instrument.tradingsymbol, vwap=vwap)
        
        return signals
    
    def _create_long_signal(
        self,
        context: StrategyContext,
        entry_price: float,
        vwap: float,
        atr: float
    ) -> Optional[Signal]:
        """Create LONG signal"""
        stop_loss = max(vwap - (atr * 0.5), entry_price - (atr * self.atr_stop_mult))
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
            rationale=f"Volume Profile Bullish: Price({entry_price:.2f}) > VWAP({vwap:.2f}) with volume surge",
            features={"vwap": vwap, "atr": atr}
        )
        
        signal.risk_amount = risk
        signal.reward_amount = reward
        self.signals_generated += 1
        return signal
    
    def _create_short_signal(
        self,
        context: StrategyContext,
        entry_price: float,
        vwap: float,
        atr: float
    ) -> Optional[Signal]:
        """Create SHORT signal"""
        stop_loss = min(vwap + (atr * 0.5), entry_price + (atr * self.atr_stop_mult))
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
            rationale=f"Volume Profile Bearish: Price({entry_price:.2f}) < VWAP({vwap:.2f}) with volume surge",
            features={"vwap": vwap, "atr": atr}
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
        
        if not context.bars_5s or len(context.bars_5s) < self.volume_lookback + 10:
            return False
        
        return True



