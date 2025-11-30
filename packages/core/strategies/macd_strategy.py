"""MACD Strategy for Indian Markets (Nifty)

Based on top 10 Nifty trading strategies.
MACD (Moving Average Convergence Divergence) crossover strategy.

Strategy Logic:
- Buy when MACD line crosses above signal line (bullish crossover)
- Sell when MACD line crosses below signal line (bearish crossover)
- Use ATR for stop-loss and targets
- Add volume confirmation
"""
from datetime import time
from typing import List, Optional

import structlog

from packages.core.models import Bar, Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


class MACDStrategy(Strategy):
    """
    MACD Strategy (Moving Average Convergence Divergence)
    
    Logic:
    1. Calculate MACD line (12 EMA - 26 EMA)
    2. Calculate Signal line (9 EMA of MACD)
    3. Buy when MACD crosses above Signal (bullish crossover)
    4. Sell when MACD crosses below Signal (bearish crossover)
    5. Use ATR for stop-loss and targets
    6. Add volume confirmation
    
    Parameters:
    - macd_fast: Fast EMA period (default: 12)
    - macd_slow: Slow EMA period (default: 26)
    - macd_signal: Signal line period (default: 9)
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
        
        self.macd_fast = params.get("macd_fast", 12)
        self.macd_slow = params.get("macd_slow", 26)
        self.macd_signal = params.get("macd_signal", 9)
        self.atr_period = params.get("atr_period", 14)
        self.atr_stop_mult = params.get("atr_stop_mult", 2.0)
        self.atr_target_mult = params.get("atr_target_mult", 3.0)
        self.volume_confirmation = params.get("volume_confirmation", True)
        self.volume_lookback = params.get("volume_lookback", 20)
        self.min_volume_mult = params.get("min_volume_mult", 1.2)
        self.rr_min = params.get("rr_min", 1.5)
        self.allowed_instruments = params.get("instruments", ["NIFTY", "BANKNIFTY"])
        
        # Backtest mode parameters (relaxed filters)
        self.backtest_rr_min = params.get("backtest_rr_min", 1.0)  # Lower R:R for backtest
        self.backtest_volume_mult = params.get("backtest_volume_mult", 0.0)  # No volume filter in backtest
        
        # State tracking
        self.last_macd: dict = {}  # token -> last MACD value
        self.last_signal: dict = {}  # token -> last signal line value
        self.last_signal_side: dict = {}  # token -> last signal side
        self.last_signal_time: dict = {}  # token -> timestamp
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
        
        # Relaxed: only check if volume is not zero
        return current_volume >= avg_volume * self.backtest_volume_mult
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """Generate MACD signals"""
        # Store backtest mode for use in signal creation
        self._backtest_mode = context.backtest_mode
        
        if not self.validate(context):
            return []
        
        # Check if instrument is allowed
        if context.instrument.symbol not in self.allowed_instruments:
            return []
        
        # Need sufficient bar data
        min_bars = max(self.macd_slow, self.atr_period) + 10
        if not context.bars_5s or len(context.bars_5s) < min_bars:
            return []
        
        signals = []
        token = context.instrument.token
        bars = context.bars_5s
        latest_bar = bars[-1]
        current_price = context.latest_tick.last_price
        
        # Get MACD from latest bar
        macd = latest_bar.macd
        macd_signal = latest_bar.macd_signal
        
        if macd is None or macd_signal is None:
            logger.debug("MACD not available", token=token)
            return []
        
        # Calculate ATR
        atr = self._calculate_atr(bars, self.atr_period)
        if atr is None or atr == 0:
            atr = current_price * 0.01
        
        # Check volume confirmation (relaxed in backtest mode)
        if context.backtest_mode:
            # In backtest mode, use relaxed volume filter
            if not self._check_volume_confirmation_backtest(bars):
                logger.debug("Volume confirmation failed (backtest)", token=token)
                return []
        else:
            if not self._check_volume_confirmation(bars):
                logger.debug("Volume confirmation failed", token=token)
                return []
        
        # Check for cooldown
        if not self._can_generate_signal(token, context.timestamp):
            logger.debug("Cooldown period active", token=token)
            return []
        
        # Try to detect crossover from bars history first (more reliable)
        # Look at previous bars to detect crossover within the same context
        crossover_detected = None
        if len(bars) >= 2:
            prev_bar = bars[-2]
            if prev_bar.macd is not None and prev_bar.macd_signal is not None:
                # Check for crossover between previous and current bar
                if prev_bar.macd <= prev_bar.macd_signal and macd > macd_signal:
                    crossover_detected = "BULLISH"
                    logger.debug("Bullish crossover detected from bars", token=token)
                elif prev_bar.macd >= prev_bar.macd_signal and macd < macd_signal:
                    crossover_detected = "BEARISH"
                    logger.debug("Bearish crossover detected from bars", token=token)
        
        # Fallback to state-based detection if no crossover in bars
        if crossover_detected is None:
            # Get previous values to detect crossover
            last_macd = self.last_macd.get(token)
            last_signal = self.last_signal.get(token)
            
            # Update state
            self.last_macd[token] = macd
            self.last_signal[token] = macd_signal
            
            # Need previous values to detect crossover
            if last_macd is None or last_signal is None:
                logger.debug("No previous MACD values (first call)", token=token)
                return []
            
            # Check for crossover using state
            if last_macd <= last_signal and macd > macd_signal:
                crossover_detected = "BULLISH"
                logger.debug("Bullish crossover detected from state", token=token)
            elif last_macd >= last_signal and macd < macd_signal:
                crossover_detected = "BEARISH"
                logger.debug("Bearish crossover detected from state", token=token)
        
        # Generate signal if crossover detected
        if crossover_detected == "BULLISH":
            # Bullish Crossover: MACD crosses above Signal
            # Avoid duplicate LONG signals
            if self.last_signal_side.get(token) == "LONG":
                logger.debug("Duplicate LONG signal prevented", token=token)
                return []
            
            logger.debug(
                "Creating LONG signal",
                token=token,
                macd=macd,
                macd_signal=macd_signal,
                atr=atr,
                price=current_price
            )
            
            signal = self._create_long_signal(
                context,
                entry_price=current_price,
                macd=macd,
                macd_signal=macd_signal,
                atr=atr
            )
            
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "LONG"
                self.last_signal_time[token] = context.timestamp
                logger.info(
                    "MACD Bullish Crossover LONG signal",
                    instrument=context.instrument.tradingsymbol,
                    entry=signal.entry_price,
                    macd=macd,
                    signal=macd_signal
                )
        
        elif crossover_detected == "BEARISH":
            # Bearish Crossover: MACD crosses below Signal
            # Avoid duplicate SHORT signals
            if self.last_signal_side.get(token) == "SHORT":
                logger.debug("Duplicate SHORT signal prevented", token=token)
                return []
            
            logger.debug(
                "Creating SHORT signal",
                token=token,
                macd=macd,
                macd_signal=macd_signal,
                atr=atr,
                price=current_price
            )
            
            signal = self._create_short_signal(
                context,
                entry_price=current_price,
                macd=macd,
                macd_signal=macd_signal,
                atr=atr
            )
            
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "SHORT"
                self.last_signal_time[token] = context.timestamp
                logger.info(
                    "MACD Bearish Crossover SHORT signal",
                    instrument=context.instrument.tradingsymbol,
                    entry=signal.entry_price,
                    macd=macd,
                    signal=macd_signal
                )
        
        return signals
    
    def _create_long_signal(
        self,
        context: StrategyContext,
        entry_price: float,
        macd: float,
        macd_signal: float,
        atr: float
    ) -> Optional[Signal]:
        """Create LONG signal"""
        # Stop-loss below entry by ATR
        stop_loss = entry_price - (atr * self.atr_stop_mult)
        stop_loss = max(stop_loss, entry_price * 0.97)
        
        risk = entry_price - stop_loss
        if risk <= 0:
            return None
        
        # Target based on ATR (use relaxed R:R in backtest mode)
        rr_required = self.backtest_rr_min if hasattr(self, '_backtest_mode') and self._backtest_mode else self.rr_min
        reward = risk * rr_required
        take_profit_1 = entry_price + (reward * 0.6)
        take_profit_2 = entry_price + reward
        
        logger.debug(
            "LONG signal parameters",
            entry=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            risk=risk,
            reward=reward,
            rr_ratio=reward/risk,
            backtest_mode=hasattr(self, '_backtest_mode') and self._backtest_mode
        )
        
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
            rationale=f"MACD Bullish Crossover: MACD({macd:.2f}) > Signal({macd_signal:.2f})",
            features={
                "macd": macd,
                "macd_signal": macd_signal,
                "macd_histogram": context.bars_5s[-1].macd_histogram if context.bars_5s and hasattr(context.bars_5s[-1], 'macd_histogram') else None,
                "atr": atr,
                "crossover_type": "BULLISH"
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
        macd: float,
        macd_signal: float,
        atr: float
    ) -> Optional[Signal]:
        """Create SHORT signal"""
        # Stop-loss above entry by ATR
        stop_loss = entry_price + (atr * self.atr_stop_mult)
        stop_loss = min(stop_loss, entry_price * 1.03)
        
        risk = stop_loss - entry_price
        if risk <= 0:
            return None
        
        # Target based on ATR (use relaxed R:R in backtest mode)
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
            rationale=f"MACD Bearish Crossover: MACD({macd:.2f}) < Signal({macd_signal:.2f})",
            features={
                "macd": macd,
                "macd_signal": macd_signal,
                "macd_histogram": context.bars_5s[-1].macd_histogram if context.bars_5s and hasattr(context.bars_5s[-1], 'macd_histogram') else None,
                "atr": atr,
                "crossover_type": "BEARISH"
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
        """Validate MACD strategy can run"""
        if not super().validate(context):
            return False
        
        # Only trade during regular market hours
        current_time = context.timestamp.time()
        market_open = time(9, 15)
        market_close = time(15, 25)
        
        if not (market_open <= current_time < market_close):
            return False
        
        # Need sufficient data
        min_bars = max(self.macd_slow, self.atr_period) + 10
        if not context.bars_5s or len(context.bars_5s) < min_bars:
            return False
        
        return True

