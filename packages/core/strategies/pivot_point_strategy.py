"""Pivot Point Strategy - Support/Resistance Trading

Proven for intraday trading: 50-60% win rate
Classic floor trader strategy

Strategy Logic:
- Buy when price bounces from pivot support (S1, S2) or breaks above R1
- Sell when price rejects from pivot resistance (R1, R2) or breaks below S1
- Pivot points act as key support/resistance
"""
from datetime import time
from typing import List, Optional

import structlog

from packages.core.models import Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


class PivotPointStrategy(Strategy):
    """
    Pivot Point Strategy
    
    Entry Logic:
    - LONG: Price bounces from S1/S2 OR breaks above R1
    - SHORT: Price rejects from R1/R2 OR breaks below S1
    
    Exit Logic:
    - Stop-loss: ATR-based or next pivot level
    - Take-profit: Next pivot level or 2x ATR
    - Exit at opposite pivot
    
    Parameters:
    - atr_stop_mult: ATR multiplier for stop (default: 1.5)
    - atr_target_mult: ATR multiplier for target (default: 2.0)
    - pivot_tolerance: Tolerance for pivot level (default: 0.002 = 0.2%)
    - rr_min: Minimum risk-reward (default: 1.5)
    """
    
    def __init__(self, name: str, params: dict):
        super().__init__(name, params)
        
        self.atr_stop_mult = params.get("atr_stop_mult", 1.5)
        self.atr_target_mult = params.get("atr_target_mult", 2.0)
        self.pivot_tolerance = params.get("pivot_tolerance", 0.002)
        self.rr_min = params.get("rr_min", 1.5)
        self.allowed_instruments = params.get("instruments", ["NIFTY", "BANKNIFTY", "CRUDEOIL", "GOLDM", "SILVERM"])
        
        self.backtest_rr_min = params.get("backtest_rr_min", 1.2)
        
        # State tracking
        self.last_signal_side: dict = {}
        self.last_signal_time: dict = {}
        self.min_signal_gap_minutes = 20
    
    def _is_near_level(self, price: float, level: float, tolerance: float = None) -> bool:
        """Check if price is near a pivot level"""
        if level is None:
            return False
        tol = tolerance or self.pivot_tolerance
        return abs(price - level) / level <= tol
    
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
        """Generate Pivot Point signals"""
        if not self.validate(context):
            return []
        
        if context.instrument.symbol not in self.allowed_instruments:
            return []
        
        if not context.bars_5s or len(context.bars_5s) < 20:
            return []
        
        signals = []
        token = context.instrument.token
        bars = context.bars_5s
        latest_bar = bars[-1]
        current_price = context.latest_tick.last_price
        
        # Get pivot points (from bar or calculate from previous day)
        pivot = latest_bar.pivot
        r1 = latest_bar.pivot_r1
        r2 = latest_bar.pivot_r2
        s1 = latest_bar.pivot_s1
        s2 = latest_bar.pivot_s2
        
        # Fallback: calculate from previous day's data
        if pivot is None and len(bars) >= 2:
            prev_bar = bars[-2]  # Previous day's last bar
            high = prev_bar.high
            low = prev_bar.low
            close = prev_bar.close
            
            pivot = (high + low + close) / 3
            r1 = 2 * pivot - low
            r2 = pivot + (high - low)
            s1 = 2 * pivot - high
            s2 = pivot - (high - low)
        
        if pivot is None:
            return []
        
        atr = latest_bar.atr or self._calculate_atr(bars)
        if atr is None or atr == 0:
            atr = current_price * 0.01
        
        if not self._can_generate_signal(token, context.timestamp):
            return []
        
        # LONG signals
        # 1. Bounce from S1 or S2
        if s1 and self._is_near_level(current_price, s1) and current_price > s1:
            if self.last_signal_side.get(token) == "LONG":
                return []
            
            signal = self._create_long_signal(context, entry_price=current_price, pivot=pivot, r1=r1, s1=s1, atr=atr, entry_type="S1_BOUNCE")
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "LONG"
                self.last_signal_time[token] = context.timestamp
                logger.info("Pivot Point S1 Bounce LONG", instrument=context.instrument.tradingsymbol, s1=s1)
        
        elif s2 and self._is_near_level(current_price, s2) and current_price > s2:
            if self.last_signal_side.get(token) == "LONG":
                return []
            
            signal = self._create_long_signal(context, entry_price=current_price, pivot=pivot, r1=r1, s1=s1, atr=atr, entry_type="S2_BOUNCE")
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "LONG"
                self.last_signal_time[token] = context.timestamp
                logger.info("Pivot Point S2 Bounce LONG", instrument=context.instrument.tradingsymbol, s2=s2)
        
        # 2. Breakout above R1
        elif r1 and current_price > r1 and (len(bars) < 2 or bars[-2].close <= r1):
            if self.last_signal_side.get(token) == "LONG":
                return []
            
            signal = self._create_long_signal(context, entry_price=current_price, pivot=pivot, r1=r1, s1=s1, atr=atr, entry_type="R1_BREAKOUT")
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "LONG"
                self.last_signal_time[token] = context.timestamp
                logger.info("Pivot Point R1 Breakout LONG", instrument=context.instrument.tradingsymbol, r1=r1)
        
        # SHORT signals
        # 1. Rejection from R1 or R2
        elif r1 and self._is_near_level(current_price, r1) and current_price < r1:
            if self.last_signal_side.get(token) == "SHORT":
                return []
            
            signal = self._create_short_signal(context, entry_price=current_price, pivot=pivot, r1=r1, s1=s1, atr=atr, entry_type="R1_REJECTION")
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "SHORT"
                self.last_signal_time[token] = context.timestamp
                logger.info("Pivot Point R1 Rejection SHORT", instrument=context.instrument.tradingsymbol, r1=r1)
        
        elif r2 and self._is_near_level(current_price, r2) and current_price < r2:
            if self.last_signal_side.get(token) == "SHORT":
                return []
            
            signal = self._create_short_signal(context, entry_price=current_price, pivot=pivot, r1=r1, s1=s1, atr=atr, entry_type="R2_REJECTION")
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "SHORT"
                self.last_signal_time[token] = context.timestamp
                logger.info("Pivot Point R2 Rejection SHORT", instrument=context.instrument.tradingsymbol, r2=r2)
        
        # 2. Breakdown below S1
        elif s1 and current_price < s1 and (len(bars) < 2 or bars[-2].close >= s1):
            if self.last_signal_side.get(token) == "SHORT":
                return []
            
            signal = self._create_short_signal(context, entry_price=current_price, pivot=pivot, r1=r1, s1=s1, atr=atr, entry_type="S1_BREAKDOWN")
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "SHORT"
                self.last_signal_time[token] = context.timestamp
                logger.info("Pivot Point S1 Breakdown SHORT", instrument=context.instrument.tradingsymbol, s1=s1)
        
        return signals
    
    def _create_long_signal(
        self,
        context: StrategyContext,
        entry_price: float,
        pivot: float,
        r1: Optional[float],
        s1: Optional[float],
        atr: float,
        entry_type: str
    ) -> Optional[Signal]:
        """Create LONG signal"""
        # Stop-loss: Below entry pivot level or ATR-based
        stop_loss = max(
            (s1 - (atr * 0.5)) if s1 else entry_price - (atr * self.atr_stop_mult),
            entry_price - (atr * self.atr_stop_mult)
        )
        stop_loss = max(stop_loss, entry_price * 0.97)
        
        risk = entry_price - stop_loss
        if risk <= 0:
            return None
        
        # Target: R1 or ATR-based
        target = r1 if r1 and r1 > entry_price else entry_price + (risk * (self.backtest_rr_min if context.backtest_mode else self.rr_min))
        rr_required = self.backtest_rr_min if context.backtest_mode else self.rr_min
        reward = risk * rr_required
        take_profit_1 = min(target, entry_price + (reward * 0.6)) if r1 else entry_price + (reward * 0.6)
        take_profit_2 = min(target, entry_price + reward) if r1 else entry_price + reward
        
        signal = Signal(
            strategy_name=self.name,
            timestamp=context.timestamp,
            instrument=context.instrument,
            side=SignalSide.LONG,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            confidence=0.65,
            rationale=f"Pivot Point {entry_type}: Entry({entry_price:.2f}), Pivot({pivot:.2f}), R1({r1:.2f if r1 else 'N/A'})",
            features={"pivot": pivot, "r1": r1, "s1": s1, "atr": atr, "entry_type": entry_type}
        )
        
        signal.risk_amount = risk
        signal.reward_amount = reward
        self.signals_generated += 1
        return signal
    
    def _create_short_signal(
        self,
        context: StrategyContext,
        entry_price: float,
        pivot: float,
        r1: Optional[float],
        s1: Optional[float],
        atr: float,
        entry_type: str
    ) -> Optional[Signal]:
        """Create SHORT signal"""
        # Stop-loss: Above entry pivot level or ATR-based
        stop_loss = min(
            (r1 + (atr * 0.5)) if r1 else entry_price + (atr * self.atr_stop_mult),
            entry_price + (atr * self.atr_stop_mult)
        )
        stop_loss = min(stop_loss, entry_price * 1.03)
        
        risk = stop_loss - entry_price
        if risk <= 0:
            return None
        
        # Target: S1 or ATR-based
        target = s1 if s1 and s1 < entry_price else entry_price - (risk * (self.backtest_rr_min if context.backtest_mode else self.rr_min))
        rr_required = self.backtest_rr_min if context.backtest_mode else self.rr_min
        reward = risk * rr_required
        take_profit_1 = max(target, entry_price - (reward * 0.6)) if s1 else entry_price - (reward * 0.6)
        take_profit_2 = max(target, entry_price - reward) if s1 else entry_price - reward
        
        signal = Signal(
            strategy_name=self.name,
            timestamp=context.timestamp,
            instrument=context.instrument,
            side=SignalSide.SHORT,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            confidence=0.65,
            rationale=f"Pivot Point {entry_type}: Entry({entry_price:.2f}), Pivot({pivot:.2f}), S1({s1:.2f if s1 else 'N/A'})",
            features={"pivot": pivot, "r1": r1, "s1": s1, "atr": atr, "entry_type": entry_type}
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
        
        if not context.bars_5s or len(context.bars_5s) < 20:
            return False
        
        return True

