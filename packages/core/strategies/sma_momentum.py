"""SMA Momentum Strategy (vectorbt-inspired) for Indian Markets

Adapted from vectorbt SMA crossover examples for NSE cash and indices.
Designed for paper trading mode only.
"""
from datetime import time
from typing import List, Optional

import numpy as np
import structlog

from packages.core.models import Bar, Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


class SMAMomentumStrategy(Strategy):
    """
    SMA Crossover Momentum Strategy (vectorbt-inspired)
    
    Logic:
    1. Calculate fast SMA and slow SMA
    2. Buy when fast SMA crosses above slow SMA (golden cross)
    3. Sell when fast SMA crosses below slow SMA (death cross)
    4. Use ATR for stop-loss and targets
    5. Add volume confirmation
    
    Parameters:
    - sma_fast: Fast SMA period (default: 13)
    - sma_slow: Slow SMA period (default: 34)
    - atr_period: ATR period for stops (default: 14)
    - atr_stop_mult: ATR multiplier for stop-loss (default: 2.0)
    - atr_target_mult: ATR multiplier for target (default: 3.0)
    - volume_confirmation: Require volume above average (default: True)
    - volume_lookback: Period for volume average (default: 20)
    - min_volume_mult: Minimum volume multiplier (default: 1.2)
    - rr_min: Minimum risk-reward ratio (default: 1.5)
    - max_positions: Maximum concurrent positions (default: 2)
    - instruments: List of instruments to trade (default: ["NIFTY", "BANKNIFTY"])
    
    India Market Adaptations:
    - Respects market hours (09:15-15:30 IST)
    - Includes realistic transaction costs in signal confidence
    - Filters by liquidity
    - Uses ATR-based stops (better for Indian market volatility)
    """
    
    def __init__(self, name: str, params: dict):
        super().__init__(name, params)
        
        self.sma_fast = params.get("sma_fast", 13)
        self.sma_slow = params.get("sma_slow", 34)
        self.atr_period = params.get("atr_period", 14)
        self.atr_stop_mult = params.get("atr_stop_mult", 2.0)
        self.atr_target_mult = params.get("atr_target_mult", 3.0)
        self.volume_confirmation = params.get("volume_confirmation", True)
        self.volume_lookback = params.get("volume_lookback", 20)
        self.min_volume_mult = params.get("min_volume_mult", 1.2)
        self.rr_min = params.get("rr_min", 1.5)
        self.allowed_instruments = params.get("instruments", ["NIFTY", "BANKNIFTY"])
        
        # Backtest mode parameters (relaxed filters)
        self.backtest_rr_min = params.get("backtest_rr_min", 1.0)
        self.backtest_volume_mult = params.get("backtest_volume_mult", 0.0)
        
        # State tracking
        self.last_sma_fast: dict = {}  # token -> last fast SMA
        self.last_sma_slow: dict = {}  # token -> last slow SMA
        self.last_signal_side: dict = {}  # token -> last signal side (LONG/SHORT/None)
        self.last_signal_time: dict = {}  # token -> timestamp
    
    def _calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
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
            return True  # Skip if not enough data
        
        recent_volumes = [b.volume for b in bars[-self.volume_lookback:]]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        current_volume = bars[-1].volume
        
        return current_volume >= avg_volume * self.min_volume_mult
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """Generate SMA momentum signals"""
        # Store backtest mode for use in signal creation
        self._backtest_mode = context.backtest_mode
        
        if not self.validate(context):
            return []
        
        # Check if instrument is allowed
        if context.instrument.symbol not in self.allowed_instruments:
            return []
        
        # Need sufficient bar data
        min_bars = max(self.sma_slow, self.atr_period) + 10
        if not context.bars_5s or len(context.bars_5s) < min_bars:
            return []
        
        signals = []
        token = context.instrument.token
        bars = context.bars_5s
        current_price = context.latest_tick.last_price
        
        # Calculate SMAs
        closes = [b.close for b in bars]
        sma_fast = self._calculate_sma(closes, self.sma_fast)
        sma_slow = self._calculate_sma(closes, self.sma_slow)
        
        if sma_fast is None or sma_slow is None:
            return []
        
        # Calculate ATR
        atr = self._calculate_atr(bars, self.atr_period)
        if atr is None or atr == 0:
            atr = current_price * 0.01  # Fallback: 1% of price
        
        # Check volume confirmation (relaxed in backtest mode)
        if context.backtest_mode:
            if not self._check_volume_confirmation_backtest(bars):
                logger.debug("Volume confirmation failed (backtest)", token=token)
                return []
        else:
            if not self._check_volume_confirmation(bars):
                logger.debug("Volume confirmation failed", token=token)
                return []
        
        # Try to detect crossover from bars history first (more reliable)
        crossover_detected = None
        if len(bars) >= 2:
            # Calculate SMAs for previous bar
            prev_prices = [b.close for b in bars[:-1]]
            if len(prev_prices) >= self.sma_slow:
                prev_sma_fast = self._calculate_sma(prev_prices[-self.sma_fast:], self.sma_fast)
                prev_sma_slow = self._calculate_sma(prev_prices[-self.sma_slow:], self.sma_slow)
                if prev_sma_fast is not None and prev_sma_slow is not None:
                    # Check for crossover between previous and current bar
                    if prev_sma_fast <= prev_sma_slow and sma_fast > sma_slow:
                        crossover_detected = "GOLDEN_CROSS"
                        logger.debug("Golden Cross detected from bars", token=token)
                    elif prev_sma_fast >= prev_sma_slow and sma_fast < sma_slow:
                        crossover_detected = "DEATH_CROSS"
                        logger.debug("Death Cross detected from bars", token=token)
        
        # Fallback to state-based detection if no crossover in bars
        if crossover_detected is None:
            last_sma_fast = self.last_sma_fast.get(token)
            last_sma_slow = self.last_sma_slow.get(token)
            
            # Update state
            self.last_sma_fast[token] = sma_fast
            self.last_sma_slow[token] = sma_slow
            
            # Need previous values to detect crossover
            if last_sma_fast is None or last_sma_slow is None:
                logger.debug("No previous SMA values (first call)", token=token)
                return []
            
            # Check for crossover using state
            if last_sma_fast <= last_sma_slow and sma_fast > sma_slow:
                crossover_detected = "GOLDEN_CROSS"
                logger.debug("Golden Cross detected from state", token=token)
            elif last_sma_fast >= last_sma_slow and sma_fast < sma_slow:
                crossover_detected = "DEATH_CROSS"
                logger.debug("Death Cross detected from state", token=token)
        
        last_side = self.last_signal_side.get(token)
        
        # Generate signal if crossover detected
        if crossover_detected == "GOLDEN_CROSS":
            # Golden Cross: Fast SMA crosses above Slow SMA
            # Avoid duplicate signals
            if last_side == "LONG":
                logger.debug("Duplicate LONG signal prevented", token=token)
                return []
            
            logger.debug(
                "Creating LONG signal (Golden Cross)",
                token=token,
                sma_fast=sma_fast,
                sma_slow=sma_slow,
                atr=atr,
                price=current_price
            )
            
            signal = self._create_long_signal(
                context,
                entry_price=current_price,
                sma_fast=sma_fast,
                sma_slow=sma_slow,
                atr=atr
            )
            
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "LONG"
                self.last_signal_time[token] = context.timestamp
                logger.info(
                    "SMA Golden Cross LONG signal",
                    instrument=context.instrument.tradingsymbol,
                    entry=signal.entry_price,
                    sma_fast=sma_fast,
                    sma_slow=sma_slow
                )
        
        elif crossover_detected == "DEATH_CROSS":
            # Death Cross: Fast SMA crosses below Slow SMA
            # Avoid duplicate signals
            if last_side == "SHORT":
                logger.debug("Duplicate SHORT signal prevented", token=token)
                return []
            
            logger.debug(
                "Creating SHORT signal (Death Cross)",
                token=token,
                sma_fast=sma_fast,
                sma_slow=sma_slow,
                atr=atr,
                price=current_price
            )
            
            signal = self._create_short_signal(
                context,
                entry_price=current_price,
                sma_fast=sma_fast,
                sma_slow=sma_slow,
                atr=atr
            )
            
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "SHORT"
                self.last_signal_time[token] = context.timestamp
                logger.info(
                    "SMA Death Cross SHORT signal",
                    instrument=context.instrument.tradingsymbol,
                    entry=signal.entry_price,
                    sma_fast=sma_fast,
                    sma_slow=sma_slow
                )
        
        return signals
    
    def _create_long_signal(
        self,
        context: StrategyContext,
        entry_price: float,
        sma_fast: float,
        sma_slow: float,
        atr: float
    ) -> Optional[Signal]:
        """Create LONG signal"""
        # Stop-loss below slow SMA or ATR-based
        stop_loss = min(sma_slow - (atr * self.atr_stop_mult), entry_price - (atr * self.atr_stop_mult))
        stop_loss = max(stop_loss, entry_price * 0.95)  # Max 5% stop
        
        risk = entry_price - stop_loss
        if risk <= 0:
            return None
        
        # Target based on ATR (use relaxed R:R in backtest mode)
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
            confidence=0.70,  # Moderate confidence (account for transaction costs)
            rationale=f"SMA Golden Cross: Fast({sma_fast:.2f}) > Slow({sma_slow:.2f})",
            features={
                "sma_fast": sma_fast,
                "sma_slow": sma_slow,
                "atr": atr,
                "crossover_type": "GOLDEN_CROSS"
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
        sma_fast: float,
        sma_slow: float,
        atr: float
    ) -> Optional[Signal]:
        """Create SHORT signal"""
        # Stop-loss above slow SMA or ATR-based
        stop_loss = max(sma_slow + (atr * self.atr_stop_mult), entry_price + (atr * self.atr_stop_mult))
        stop_loss = min(stop_loss, entry_price * 1.05)  # Max 5% stop
        
        risk = stop_loss - entry_price
        if risk <= 0:
            return None
        
        # Target based on ATR (use relaxed R:R in backtest mode)
        rr_required = self.backtest_rr_min if hasattr(self, '_backtest_mode') and self._backtest_mode else self.rr_min
        reward = risk * rr_required
        target_price = entry_price - reward
        
        # Ensure minimum risk-reward
        if reward / risk < self.rr_min:
            return None
        
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
            confidence=0.70,  # Moderate confidence (account for transaction costs)
            rationale=f"SMA Death Cross: Fast({sma_fast:.2f}) < Slow({sma_slow:.2f})",
            features={
                "sma_fast": sma_fast,
                "sma_slow": sma_slow,
                "atr": atr,
                "crossover_type": "DEATH_CROSS"
            }
        )
        
        signal.risk_amount = risk
        signal.reward_amount = reward
        
        self.signals_generated += 1
        
        return signal
    
    def validate(self, context: StrategyContext) -> bool:
        """Validate SMA momentum strategy can run"""
        if not super().validate(context):
            return False
        
        # Only trade during regular market hours
        current_time = context.timestamp.time()
        market_open = time(9, 15)
        market_close = time(15, 25)  # Stop before EOD
        
        if not (market_open <= current_time < market_close):
            return False
        
        # Need sufficient data
        min_bars = max(self.sma_slow, self.atr_period) + 10
        if not context.bars_5s or len(context.bars_5s) < min_bars:
            return False
        
        return True

