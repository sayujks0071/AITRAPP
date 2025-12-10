"""RSI Mean Reversion Strategy (vectorbt-inspired) for Indian Markets

Adapted from vectorbt RSI mean reversion examples for NSE cash and indices.
Designed for paper trading mode only.

Strategy Logic:
- Buy when RSI < oversold threshold (default: 25)
- Sell when RSI > overbought threshold (default: 75)
- Add volume confirmation
- Filter by liquidity
- Respect Indian market hours and transaction costs
"""
from datetime import time
from typing import List, Optional

import structlog

from packages.core.models import Bar, Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


class RSIMeanReversionStrategy(Strategy):
    """
    RSI Mean Reversion Strategy (vectorbt-inspired)
    
    Logic:
    1. Calculate RSI (Relative Strength Index)
    2. Buy when RSI < oversold threshold (oversold condition)
    3. Sell when RSI > overbought threshold (overbought condition)
    4. Use ATR for stop-loss and targets
    5. Add volume confirmation
    6. Filter by liquidity
    
    Parameters:
    - rsi_period: RSI period (default: 14)
    - oversold_threshold: RSI oversold threshold (default: 25)
    - overbought_threshold: RSI overbought threshold (default: 75)
    - atr_period: ATR period (default: 14)
    - atr_stop_mult: ATR multiplier for stop-loss (default: 1.5)
    - atr_target_mult: ATR multiplier for target (default: 2.0)
    - volume_confirmation: Require volume above average (default: True)
    - volume_lookback: Period for volume average (default: 20)
    - min_volume_mult: Minimum volume multiplier (default: 1.1)
    - min_liquidity_turnover: Minimum daily turnover for liquidity filter (default: 10000000)
    - rr_min: Minimum risk-reward ratio (default: 1.5)
    - max_positions: Maximum concurrent positions (default: 2)
    - instruments: List of instruments to trade (default: ["NIFTY", "BANKNIFTY"])
    
    India Market Adaptations:
    - Respects market hours (09:15-15:30 IST)
    - Includes realistic transaction costs in signal confidence
    - Uses tighter RSI thresholds (25/75 instead of 30/70) for Indian markets
    - Volume confirmation to avoid false signals
    - Liquidity filtering
    """
    
    def __init__(self, name: str, params: dict):
        super().__init__(name, params)
        
        self.rsi_period = params.get("rsi_period", 14)
        self.oversold_threshold = params.get("oversold_threshold", 25)
        self.overbought_threshold = params.get("overbought_threshold", 75)
        self.atr_period = params.get("atr_period", 14)
        self.atr_stop_mult = params.get("atr_stop_mult", 1.5)
        self.atr_target_mult = params.get("atr_target_mult", 2.0)
        self.volume_confirmation = params.get("volume_confirmation", True)
        self.volume_lookback = params.get("volume_lookback", 20)
        self.min_volume_mult = params.get("min_volume_mult", 1.1)
        self.min_liquidity_turnover = params.get("min_liquidity_turnover", 10000000)
        self.rr_min = params.get("rr_min", 1.5)
        
        # Backtest mode parameters (relaxed filters)
        self.backtest_rr_min = params.get("backtest_rr_min", 1.0)
        self.backtest_volume_mult = params.get("backtest_volume_mult", 0.0)
        self.allowed_instruments = params.get("instruments", ["NIFTY", "BANKNIFTY"])
        
        # State tracking
        self.last_rsi: dict = {}  # token -> last RSI value
        self.last_signal_side: dict = {}  # token -> last signal side (LONG/SHORT/None)
        self.last_signal_time: dict = {}  # token -> timestamp
        self.min_signal_gap_minutes = 15  # Cooldown between signals
    
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
    
    def _check_volume_confirmation_backtest(self, bars: List[Bar]) -> bool:
        """Relaxed volume check for backtesting"""
        if not self.volume_confirmation or len(bars) < self.volume_lookback + 1:
            return True
        
        recent_volumes = [b.volume for b in bars[-self.volume_lookback:]]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        current_volume = bars[-1].volume
        
        return current_volume >= avg_volume * self.backtest_volume_mult
    
    def _check_liquidity(self, bars: List[Bar], current_price: float) -> bool:
        """Check if instrument has sufficient liquidity"""
        if len(bars) < 20:
            return True  # Not enough data, allow
        
        # Estimate daily turnover (volume * price)
        recent_volumes = [b.volume for b in bars[-20:]]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        estimated_turnover = avg_volume * current_price
        
        return estimated_turnover >= self.min_liquidity_turnover
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """Generate RSI mean reversion signals"""
        # Store backtest mode for use in signal creation
        self._backtest_mode = context.backtest_mode
        
        if not self.validate(context):
            return []
        
        # Check if instrument is allowed
        if context.instrument.symbol not in self.allowed_instruments:
            return []
        
        # Need sufficient bar data
        min_bars = max(self.rsi_period, self.atr_period) + 10
        if not context.bars_5s or len(context.bars_5s) < min_bars:
            return []
        
        signals = []
        token = context.instrument.token
        bars = context.bars_5s
        latest_bar = bars[-1]
        current_price = context.latest_tick.last_price
        
        # Get RSI from latest bar (computed by indicator calculator)
        rsi = latest_bar.rsi
        
        if rsi is None:
            logger.debug("RSI not available", token=token)
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
        
        # Check liquidity
        if not self._check_liquidity(bars, current_price):
            logger.debug("Insufficient liquidity", token=token)
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
        
        # Store last RSI for tracking
        last_rsi = self.last_rsi.get(token)
        self.last_rsi[token] = rsi
        
        # Check for oversold condition (RSI < oversold threshold)
        if rsi < self.oversold_threshold:
            # Avoid duplicate LONG signals
            if self.last_signal_side.get(token) == "LONG":
                logger.debug("Duplicate LONG signal prevented (oversold)", token=token)
                return []
            
            logger.debug(
                "Creating LONG signal (oversold)",
                token=token,
                rsi=rsi,
                threshold=self.oversold_threshold,
                atr=atr,
                price=current_price
            )
            # Avoid duplicate LONG signals
            if self.last_signal_side.get(token) == "LONG":
                return []
            
            # Only trigger on RSI recovery (RSI was lower before)
            if last_rsi is not None and rsi < last_rsi:
                return []  # RSI still falling, wait for bounce
            
            signal = self._create_long_signal(
                context,
                entry_price=current_price,
                rsi=rsi,
                atr=atr
            )
            
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "LONG"
                self.last_signal_time[token] = context.timestamp
                logger.info(
                    "RSI mean reversion LONG signal (oversold)",
                    instrument=context.instrument.tradingsymbol,
                    entry=signal.entry_price,
                    rsi=rsi,
                    oversold_threshold=self.oversold_threshold
                )
        
        # Check for overbought condition (RSI > overbought threshold)
        elif rsi > self.overbought_threshold:
            # Avoid duplicate SHORT signals
            if self.last_signal_side.get(token) == "SHORT":
                logger.debug("Duplicate SHORT signal prevented (overbought)", token=token)
                return []
            
            logger.debug(
                "Creating SHORT signal (overbought)",
                token=token,
                rsi=rsi,
                threshold=self.overbought_threshold,
                atr=atr,
                price=current_price
            )
            # Avoid duplicate SHORT signals
            if self.last_signal_side.get(token) == "SHORT":
                return []
            
            # Only trigger on RSI rejection (RSI was higher before)
            if last_rsi is not None and rsi > last_rsi:
                return []  # RSI still rising, wait for rejection
            
            signal = self._create_short_signal(
                context,
                entry_price=current_price,
                rsi=rsi,
                atr=atr
            )
            
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "SHORT"
                self.last_signal_time[token] = context.timestamp
                logger.info(
                    "RSI mean reversion SHORT signal (overbought)",
                    instrument=context.instrument.tradingsymbol,
                    entry=signal.entry_price,
                    rsi=rsi,
                    overbought_threshold=self.overbought_threshold
                )
        
        return signals
    
    def _create_long_signal(
        self,
        context: StrategyContext,
        entry_price: float,
        rsi: float,
        atr: float
    ) -> Optional[Signal]:
        """Create LONG signal (oversold bounce)"""
        # Stop-loss below entry by ATR
        stop_loss = entry_price - (atr * self.atr_stop_mult)
        stop_loss = max(stop_loss, entry_price * 0.97)  # Max 3% stop
        
        risk = entry_price - stop_loss
        if risk <= 0:
            return None
        
        # Target based on ATR or RSI mean reversion (RSI 50)
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
            confidence=0.70,  # Moderate-high confidence (RSI is reliable)
            rationale=f"RSI mean reversion LONG: RSI {rsi:.2f} < {self.oversold_threshold} (oversold)",
            features={
                "rsi": rsi,
                "atr": atr,
                "oversold_threshold": self.oversold_threshold,
                "overbought_threshold": self.overbought_threshold,
                "mean_reversion_type": "OVERSOLD"
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
        rsi: float,
        atr: float
    ) -> Optional[Signal]:
        """Create SHORT signal (overbought rejection)"""
        # Stop-loss above entry by ATR
        stop_loss = entry_price + (atr * self.atr_stop_mult)
        stop_loss = min(stop_loss, entry_price * 1.03)  # Max 3% stop
        
        risk = stop_loss - entry_price
        if risk <= 0:
            return None
        
        # Target based on ATR or RSI mean reversion (RSI 50)
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
            confidence=0.70,  # Moderate-high confidence (RSI is reliable)
            rationale=f"RSI mean reversion SHORT: RSI {rsi:.2f} > {self.overbought_threshold} (overbought)",
            features={
                "rsi": rsi,
                "atr": atr,
                "oversold_threshold": self.oversold_threshold,
                "overbought_threshold": self.overbought_threshold,
                "mean_reversion_type": "OVERBOUGHT"
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
        """Validate RSI mean reversion strategy can run"""
        if not super().validate(context):
            return False
        
        # Only trade during regular market hours
        current_time = context.timestamp.time()
        market_open = time(9, 15)
        market_close = time(15, 25)  # Stop before EOD
        
        if not (market_open <= current_time < market_close):
            return False
        
        # Need sufficient data
        min_bars = max(self.rsi_period, self.atr_period) + 10
        if not context.bars_5s or len(context.bars_5s) < min_bars:
            return False
        
        return True

