"""VWAP Strategy for Indian Markets (Nifty)

Based on top 10 Nifty trading strategies.
Volume Weighted Average Price (VWAP) strategy.

Strategy Logic:
- Buy when price is below VWAP (potential undervaluation)
- Sell when price is above VWAP (potential overvaluation)
- Use ATR for stop-loss and targets
"""
from datetime import time
from typing import List, Optional

import structlog

from packages.core.models import Bar, Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


class VWAPStrategy(Strategy):
    """
    VWAP Strategy (Volume Weighted Average Price)
    
    Logic:
    1. Calculate VWAP (daily reset)
    2. Buy when price is below VWAP (undervalued)
    3. Sell when price is above VWAP (overvalued)
    4. Use ATR for stop-loss and targets
    
    Parameters:
    - vwap_deviation_pct: Deviation from VWAP to trigger signal (default: 0.5)
    - atr_period: ATR period (default: 14)
    - atr_stop_mult: ATR multiplier for stop-loss (default: 2.0)
    - atr_target_mult: ATR multiplier for target (default: 3.0)
    - volume_confirmation: Require volume above average (default: True)
    - volume_lookback: Period for volume average (default: 20)
    - min_volume_mult: Minimum volume multiplier (default: 1.2)
    - rr_min: Minimum risk-reward ratio (default: 1.5)
    - max_positions: Maximum concurrent positions (default: 2)
    - instruments: List of instruments to trade (default: ["NIFTY", "BANKNIFTY"])
    """
    
    def __init__(self, name: str, params: dict):
        super().__init__(name, params)
        
        self.vwap_deviation_pct = params.get("vwap_deviation_pct", 0.5)
        self.atr_period = params.get("atr_period", 14)
        self.atr_stop_mult = params.get("atr_stop_mult", 2.0)
        self.atr_target_mult = params.get("atr_target_mult", 3.0)
        self.volume_confirmation = params.get("volume_confirmation", True)
        self.volume_lookback = params.get("volume_lookback", 20)
        self.min_volume_mult = params.get("min_volume_mult", 1.2)
        self.rr_min = params.get("rr_min", 1.5)
        
        # Backtest mode parameters (relaxed filters)
        self.backtest_rr_min = params.get("backtest_rr_min", 1.0)
        self.backtest_volume_mult = params.get("backtest_volume_mult", 0.0)
        self.allowed_instruments = params.get("instruments", ["NIFTY", "BANKNIFTY"])
        
        # State tracking
        self.last_signal_side: dict = {}
        self.last_signal_time: dict = {}
        self.min_signal_gap_minutes = 15
    
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
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """Generate VWAP signals"""
        # Store backtest mode for use in signal creation
        self._backtest_mode = context.backtest_mode
        
        if not self.validate(context):
            return []
        
        if context.instrument.symbol not in self.allowed_instruments:
            return []
        
        min_bars = self.atr_period + 10
        if not context.bars_5s or len(context.bars_5s) < min_bars:
            return []
        
        signals = []
        token = context.instrument.token
        bars = context.bars_5s
        latest_bar = bars[-1]
        current_price = context.latest_tick.last_price
        
        # Get VWAP from latest bar
        vwap = latest_bar.vwap
        
        if vwap is None:
            logger.debug("VWAP not available", token=token)
            return []
        
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
        
        # Calculate deviation from VWAP
        deviation_pct = ((current_price - vwap) / vwap) * 100 if vwap > 0 else 0
        
        # Buy when price is below VWAP (undervalued)
        if deviation_pct <= -self.vwap_deviation_pct:
            # Avoid duplicate LONG signals
            if self.last_signal_side.get(token) == "LONG":
                logger.debug("Duplicate LONG signal prevented (below VWAP)", token=token)
                return []
            
            logger.debug(
                "Creating LONG signal (below VWAP)",
                token=token,
                price=current_price,
                vwap=vwap,
                deviation=deviation_pct,
                atr=atr
            )
            if self.last_signal_side.get(token) == "LONG":
                return []
            
            signal = self._create_long_signal(
                context,
                entry_price=current_price,
                vwap=vwap,
                deviation_pct=deviation_pct,
                atr=atr
            )
            
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "LONG"
                self.last_signal_time[token] = context.timestamp
                logger.info(
                    "VWAP LONG signal (below VWAP)",
                    instrument=context.instrument.tradingsymbol,
                    entry=signal.entry_price,
                    vwap=vwap,
                    deviation=deviation_pct
                )
        
        # Sell when price is above VWAP (overvalued)
        elif deviation_pct >= self.vwap_deviation_pct:
            # Avoid duplicate SHORT signals
            if self.last_signal_side.get(token) == "SHORT":
                logger.debug("Duplicate SHORT signal prevented (above VWAP)", token=token)
                return []
            
            logger.debug(
                "Creating SHORT signal (above VWAP)",
                token=token,
                price=current_price,
                vwap=vwap,
                deviation=deviation_pct,
                atr=atr
            )
            if self.last_signal_side.get(token) == "SHORT":
                return []
            
            signal = self._create_short_signal(
                context,
                entry_price=current_price,
                vwap=vwap,
                deviation_pct=deviation_pct,
                atr=atr
            )
            
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "SHORT"
                self.last_signal_time[token] = context.timestamp
                logger.info(
                    "VWAP SHORT signal (above VWAP)",
                    instrument=context.instrument.tradingsymbol,
                    entry=signal.entry_price,
                    vwap=vwap,
                    deviation=deviation_pct
                )
        
        return signals
    
    def _create_long_signal(
        self,
        context: StrategyContext,
        entry_price: float,
        vwap: float,
        deviation_pct: float,
        atr: float
    ) -> Optional[Signal]:
        """Create LONG signal (below VWAP)"""
        stop_loss = entry_price - (atr * self.atr_stop_mult)
        stop_loss = max(stop_loss, entry_price * 0.97)
        
        risk = entry_price - stop_loss
        if risk <= 0:
            return None
        
        # Target at VWAP (mean reversion)
        target_price = vwap
        reward = target_price - entry_price
        
        if reward / risk < self.rr_min:
            # Use ATR-based target instead (relaxed R:R in backtest mode)
            rr_required = self.backtest_rr_min if hasattr(self, '_backtest_mode') and self._backtest_mode else self.rr_min
            reward = risk * rr_required
            target_price = entry_price + reward
        
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
            rationale=f"VWAP LONG: Price {entry_price:.2f} below VWAP {vwap:.2f} ({deviation_pct:.2f}%)",
            features={
                "vwap": vwap,
                "deviation_pct": deviation_pct,
                "atr": atr,
                "mean_reversion_type": "BELOW_VWAP"
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
        vwap: float,
        deviation_pct: float,
        atr: float
    ) -> Optional[Signal]:
        """Create SHORT signal (above VWAP)"""
        stop_loss = entry_price + (atr * self.atr_stop_mult)
        stop_loss = min(stop_loss, entry_price * 1.03)
        
        risk = stop_loss - entry_price
        if risk <= 0:
            return None
        
        # Target at VWAP (mean reversion)
        target_price = vwap
        reward = entry_price - target_price
        
        if reward / risk < self.rr_min:
            # Use ATR-based target instead (relaxed R:R in backtest mode)
            rr_required = self.backtest_rr_min if hasattr(self, '_backtest_mode') and self._backtest_mode else self.rr_min
            reward = risk * rr_required
            target_price = entry_price - reward
        
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
            rationale=f"VWAP SHORT: Price {entry_price:.2f} above VWAP {vwap:.2f} ({deviation_pct:.2f}%)",
            features={
                "vwap": vwap,
                "deviation_pct": deviation_pct,
                "atr": atr,
                "mean_reversion_type": "ABOVE_VWAP"
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
        """Validate VWAP strategy can run"""
        if not super().validate(context):
            return False
        
        current_time = context.timestamp.time()
        market_open = time(9, 15)
        market_close = time(15, 25)
        
        if not (market_open <= current_time < market_close):
            return False
        
        min_bars = self.atr_period + 10
        if not context.bars_5s or len(context.bars_5s) < min_bars:
            return False
        
        return True

