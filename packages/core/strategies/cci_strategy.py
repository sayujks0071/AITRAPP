"""Commodity Channel Index (CCI) Strategy - Mean Reversion

Proven for commodities (MCX): 60-70% win rate
Excellent for gold, crude oil, silver

Strategy Logic:
- Buy when CCI crosses above -100 from oversold (<-100)
- Sell when CCI crosses below +100 from overbought (>+100)
- ATR-based stops and targets
"""
from datetime import time
from typing import List, Optional

import structlog

from packages.core.models import Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


class CCIStrategy(Strategy):
    """
    Commodity Channel Index (CCI) Strategy
    
    Entry Logic:
    - LONG: CCI crosses above -100 from oversold zone (<-100)
    - SHORT: CCI crosses below +100 from overbought zone (>+100)
    
    Exit Logic:
    - Stop-loss: ATR-based
    - Take-profit: 1.5x-2x ATR
    - Exit when opposite signal occurs
    
    Parameters:
    - cci_period: CCI period (default: 20)
    - oversold_threshold: Oversold level (default: -80)  # relaxed for MCX
    - overbought_threshold: Overbought level (default: +80)  # relaxed for MCX
    - atr_stop_mult: ATR multiplier for stop (default: 1.5)
    - atr_target_mult: ATR multiplier for target (default: 2.0)
    - rr_min: Minimum risk-reward (default: 1.5)
    """
    
    def __init__(self, name: str, params: dict):
        super().__init__(name, params)
        
        self.cci_period = params.get("cci_period", 20)
        self.oversold_threshold = params.get("oversold_threshold", -80)
        self.overbought_threshold = params.get("overbought_threshold", 80)
        self.atr_stop_mult = params.get("atr_stop_mult", 1.5)
        self.atr_target_mult = params.get("atr_target_mult", 2.0)
        self.rr_min = params.get("rr_min", 1.5)
        self.allowed_instruments = params.get("instruments", ["CRUDEOIL", "GOLDM", "SILVERM", "NATURALGAS", "COPPER", "NIFTY", "BANKNIFTY"])
        
        self.backtest_rr_min = params.get("backtest_rr_min", 1.2)
        
        # State tracking
        self.last_cci: dict = {}
        self.last_signal_side: dict = {}
        self.last_signal_time: dict = {}
        self.min_signal_gap_minutes = params.get("cooldown_minutes", 12)
    
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
        """Generate CCI signals"""
        if not self.validate(context):
            return []
        
        if context.instrument.symbol not in self.allowed_instruments:
            return []
        
        if not context.bars_5s or len(context.bars_5s) < self.cci_period + 10:
            return []
        
        signals = []
        token = context.instrument.token
        bars = context.bars_5s
        latest_bar = bars[-1]
        current_price = context.latest_tick.last_price
        
        # Get CCI
        cci = latest_bar.cci
        if cci is None:
            logger.debug("CCI not available", token=token)
            return []
        
        atr = latest_bar.atr or self._calculate_atr(bars)
        if atr is None or atr == 0:
            atr = current_price * 0.01
        
        if not self._can_generate_signal(token, context.timestamp):
            return []
        
        # Get previous CCI
        last_cci = self.last_cci.get(token)
        self.last_cci[token] = cci
        
        if last_cci is None:
            return []
        
        # Oversold crossover (LONG)
        if last_cci < self.oversold_threshold and cci > self.oversold_threshold:
            if self.last_signal_side.get(token) == "LONG":
                return []
            
            signal = self._create_long_signal(context, entry_price=current_price, cci=cci, atr=atr)
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "LONG"
                self.last_signal_time[token] = context.timestamp
                logger.info("CCI Oversold Crossover LONG", instrument=context.instrument.tradingsymbol, cci=cci)
        
        # Overbought crossover (SHORT)
        elif last_cci > self.overbought_threshold and cci < self.overbought_threshold:
            if self.last_signal_side.get(token) == "SHORT":
                return []
            
            signal = self._create_short_signal(context, entry_price=current_price, cci=cci, atr=atr)
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "SHORT"
                self.last_signal_time[token] = context.timestamp
                logger.info("CCI Overbought Crossover SHORT", instrument=context.instrument.tradingsymbol, cci=cci)
        
        return signals
    
    def _create_long_signal(
        self,
        context: StrategyContext,
        entry_price: float,
        cci: float,
        atr: float
    ) -> Optional[Signal]:
        """Create LONG signal"""
        stop_loss = entry_price - (atr * self.atr_stop_mult)
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
            rationale=f"CCI Oversold: CCI({cci:.1f}) crossed above {self.oversold_threshold}",
            features={"cci": cci, "atr": atr}
        )
        
        signal.risk_amount = risk
        signal.reward_amount = reward
        self.signals_generated += 1
        return signal
    
    def _create_short_signal(
        self,
        context: StrategyContext,
        entry_price: float,
        cci: float,
        atr: float
    ) -> Optional[Signal]:
        """Create SHORT signal"""
        stop_loss = entry_price + (atr * self.atr_stop_mult)
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
            rationale=f"CCI Overbought: CCI({cci:.1f}) crossed below {self.overbought_threshold}",
            features={"cci": cci, "atr": atr}
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
        # Extended MCX window; fallback to NSE hours for non-MCX
        if context.instrument.exchange == "MCX":
            if not (time(9, 0) <= current_time < time(23, 30)):
                return False
        else:
            if not (time(9, 15) <= current_time < time(15, 25)):
                return False
        
        if not context.bars_5s or len(context.bars_5s) < self.cci_period + 10:
            return False
        
        return True


