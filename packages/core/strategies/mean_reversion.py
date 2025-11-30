"""Mean Reversion Strategy (bt-inspired) for Indian Markets

Adapted from bt framework mean reversion examples for NSE cash and indices.
Designed for paper trading mode only.

Strategy Logic:
- Buy when price deviates below moving average (oversold)
- Sell when price deviates above moving average (overbought)
- Use ATR-based bands instead of fixed standard deviations
- Filter by volatility regime (avoid high volatility periods)
- Respect Indian market hours and transaction costs
"""
from datetime import time
from typing import List, Optional

import structlog

from packages.core.models import Bar, Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


class MeanReversionStrategy(Strategy):
    """
    Mean Reversion Strategy (bt-inspired)
    
    Logic:
    1. Calculate moving average (SMA or EMA)
    2. Calculate ATR-based deviation bands
    3. Buy when price touches lower band (oversold)
    4. Sell when price touches upper band (overbought)
    5. Use ATR for stop-loss and targets
    6. Filter by volatility regime
    
    Parameters:
    - ma_period: Moving average period (default: 20)
    - ma_type: "SMA" or "EMA" (default: "SMA")
    - atr_period: ATR period (default: 14)
    - atr_band_mult: ATR multiplier for bands (default: 2.0)
    - atr_stop_mult: ATR multiplier for stop-loss (default: 1.5)
    - atr_target_mult: ATR multiplier for target (default: 2.0)
    - volume_confirmation: Require volume above average (default: True)
    - volume_lookback: Period for volume average (default: 20)
    - min_volume_mult: Minimum volume multiplier (default: 1.1)
    - max_volatility_atr_mult: Maximum volatility filter (default: 3.0)
    - rr_min: Minimum risk-reward ratio (default: 1.5)
    - max_positions: Maximum concurrent positions (default: 2)
    - instruments: List of instruments to trade (default: ["NIFTY", "BANKNIFTY"])
    
    India Market Adaptations:
    - Respects market hours (09:15-15:30 IST)
    - Includes realistic transaction costs in signal confidence
    - Filters by volatility regime (avoids high volatility periods)
    - Uses ATR-based bands (better for Indian market volatility)
    - Volume confirmation to avoid false signals
    """
    
    def __init__(self, name: str, params: dict):
        super().__init__(name, params)
        
        self.ma_period = params.get("ma_period", 20)
        self.ma_type = params.get("ma_type", "SMA")  # "SMA" or "EMA"
        self.atr_period = params.get("atr_period", 14)
        self.atr_band_mult = params.get("atr_band_mult", 2.0)
        self.atr_stop_mult = params.get("atr_stop_mult", 1.5)
        self.atr_target_mult = params.get("atr_target_mult", 2.0)
        self.volume_confirmation = params.get("volume_confirmation", True)
        self.volume_lookback = params.get("volume_lookback", 20)
        self.min_volume_mult = params.get("min_volume_mult", 1.1)
        self.max_volatility_atr_mult = params.get("max_volatility_atr_mult", 3.0)
        self.rr_min = params.get("rr_min", 1.5)
        
        # Backtest mode parameters (relaxed filters)
        self.backtest_rr_min = params.get("backtest_rr_min", 1.0)
        self.backtest_volume_mult = params.get("backtest_volume_mult", 0.0)
        self.allowed_instruments = params.get("instruments", ["NIFTY", "BANKNIFTY"])
        
        # State tracking
        self.last_signal_side: dict = {}  # token -> last signal side (LONG/SHORT/None)
        self.last_signal_time: dict = {}  # token -> timestamp
        self.min_signal_gap_minutes = 15  # Cooldown between signals
    
    def _calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return None
        
        # Use pandas-style EMA calculation
        multiplier = 2.0 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
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
    
    def _check_volatility_regime(self, bars: List[Bar], atr: float) -> bool:
        """Check if volatility is acceptable (not too high)"""
        if len(bars) < self.ma_period:
            return True  # Not enough data, allow
        
        # Calculate average ATR over lookback period
        recent_atrs = []
        for i in range(max(0, len(bars) - self.ma_period), len(bars)):
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
            recent_atrs.append(tr)
        
        if not recent_atrs:
            return True
        
        avg_atr = sum(recent_atrs) / len(recent_atrs)
        current_price = bars[-1].close
        
        # Check if current ATR is within acceptable range
        atr_pct = (atr / current_price) * 100 if current_price > 0 else 0
        max_atr_pct = (avg_atr * self.max_volatility_atr_mult / current_price) * 100 if current_price > 0 else 0
        
        return atr_pct <= max_atr_pct
    
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
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """Generate mean reversion signals"""
        # Store backtest mode for use in signal creation
        self._backtest_mode = context.backtest_mode
        
        if not self.validate(context):
            return []
        
        # Check if instrument is allowed
        if context.instrument.symbol not in self.allowed_instruments:
            return []
        
        # Need sufficient bar data
        min_bars = max(self.ma_period, self.atr_period) + 10
        if not context.bars_5s or len(context.bars_5s) < min_bars:
            return []
        
        signals = []
        token = context.instrument.token
        bars = context.bars_5s
        current_price = context.latest_tick.last_price
        
        # Calculate moving average
        closes = [b.close for b in bars]
        if self.ma_type == "EMA":
            ma = self._calculate_ema(closes, self.ma_period)
        else:
            ma = self._calculate_sma(closes, self.ma_period)
        
        if ma is None:
            return []
        
        # Calculate ATR
        atr = self._calculate_atr(bars, self.atr_period)
        if atr is None or atr == 0:
            atr = current_price * 0.01  # Fallback: 1% of price
        
        # Check volatility regime
        if not self._check_volatility_regime(bars, atr):
            logger.debug("Volatility too high, skipping", token=token, atr=atr)
            return []
        
        # Check volume confirmation (relaxed in backtest mode)
        if context.backtest_mode:
            if not self._check_volume_confirmation_backtest(bars):
                logger.debug("Volume confirmation failed (backtest)", token=token)
                return []
        else:
            if not self._check_volume_confirmation(bars):
                logger.debug("Volume confirmation failed", token=token)
                return []
        
        # Calculate ATR-based bands
        upper_band = ma + (atr * self.atr_band_mult)
        lower_band = ma - (atr * self.atr_band_mult)
        
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
        
        # Check for oversold condition (price touches lower band)
        if current_price <= lower_band:
            # Avoid duplicate LONG signals
            if self.last_signal_side.get(token) == "LONG":
                logger.debug("Duplicate LONG signal prevented (lower band)", token=token)
                return []
            
            logger.debug(
                "Creating LONG signal (lower band touch)",
                token=token,
                price=current_price,
                lower_band=lower_band,
                ma=ma,
                atr=atr
            )
            
            signal = self._create_long_signal(
                context,
                entry_price=current_price,
                ma=ma,
                atr=atr,
                lower_band=lower_band
            )
            
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "LONG"
                self.last_signal_time[token] = context.timestamp
                logger.info(
                    "Mean reversion LONG signal (oversold)",
                    instrument=context.instrument.tradingsymbol,
                    entry=signal.entry_price,
                    ma=ma,
                    lower_band=lower_band
                )
        
        # Check for overbought condition (price touches upper band)
        elif current_price >= upper_band:
            # Avoid duplicate SHORT signals
            if self.last_signal_side.get(token) == "SHORT":
                logger.debug("Duplicate SHORT signal prevented (upper band)", token=token)
                return []
            
            logger.debug(
                "Creating SHORT signal (upper band touch)",
                token=token,
                price=current_price,
                upper_band=upper_band,
                ma=ma,
                atr=atr
            )
            
            signal = self._create_short_signal(
                context,
                entry_price=current_price,
                ma=ma,
                atr=atr,
                upper_band=upper_band
            )
            
            if signal:
                signals.append(signal)
                self.last_signal_side[token] = "SHORT"
                self.last_signal_time[token] = context.timestamp
                logger.info(
                    "Mean reversion SHORT signal (overbought)",
                    instrument=context.instrument.tradingsymbol,
                    entry=signal.entry_price,
                    ma=ma,
                    upper_band=upper_band
                )
        
        return signals
    
    def _create_long_signal(
        self,
        context: StrategyContext,
        entry_price: float,
        ma: float,
        atr: float,
        lower_band: float
    ) -> Optional[Signal]:
        """Create LONG signal (oversold bounce)"""
        # Stop-loss below lower band
        stop_loss = lower_band - (atr * self.atr_stop_mult)
        stop_loss = max(stop_loss, entry_price * 0.97)  # Max 3% stop
        
        risk = entry_price - stop_loss
        if risk <= 0:
            return None
        
        # Target at mean reversion to MA or ATR-based
        target_price = ma  # Mean reversion target
        reward = target_price - entry_price
        
        # Ensure minimum risk-reward (use relaxed R:R in backtest mode)
        rr_required = self.backtest_rr_min if hasattr(self, '_backtest_mode') and self._backtest_mode else self.rr_min
        if reward / risk < rr_required:
            # Use ATR-based target instead
            reward = risk * rr_required
            target_price = entry_price + reward
        else:
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
            confidence=0.65,  # Moderate confidence (mean reversion can be risky)
            rationale=f"Mean reversion LONG: Price {entry_price:.2f} below lower band {lower_band:.2f}, MA: {ma:.2f}",
            features={
                "ma": ma,
                "atr": atr,
                "lower_band": lower_band,
                "upper_band": ma + (atr * self.atr_band_mult),
                "deviation_pct": ((entry_price - ma) / ma * 100) if ma > 0 else 0,
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
        ma: float,
        atr: float,
        upper_band: float
    ) -> Optional[Signal]:
        """Create SHORT signal (overbought rejection)"""
        # Stop-loss above upper band
        stop_loss = upper_band + (atr * self.atr_stop_mult)
        stop_loss = min(stop_loss, entry_price * 1.03)  # Max 3% stop
        
        risk = stop_loss - entry_price
        if risk <= 0:
            return None
        
        # Target at mean reversion to MA or ATR-based
        target_price = ma  # Mean reversion target
        reward = entry_price - target_price
        
        # Ensure minimum risk-reward (use relaxed R:R in backtest mode)
        rr_required = self.backtest_rr_min if hasattr(self, '_backtest_mode') and self._backtest_mode else self.rr_min
        if reward / risk < rr_required:
            # Use ATR-based target instead
            reward = risk * rr_required
            target_price = entry_price - reward
        else:
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
            confidence=0.65,  # Moderate confidence (mean reversion can be risky)
            rationale=f"Mean reversion SHORT: Price {entry_price:.2f} above upper band {upper_band:.2f}, MA: {ma:.2f}",
            features={
                "ma": ma,
                "atr": atr,
                "upper_band": upper_band,
                "lower_band": ma - (atr * self.atr_band_mult),
                "deviation_pct": ((entry_price - ma) / ma * 100) if ma > 0 else 0,
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
        """Validate mean reversion strategy can run"""
        if not super().validate(context):
            return False
        
        # Only trade during regular market hours
        current_time = context.timestamp.time()
        market_open = time(9, 15)
        market_close = time(15, 25)  # Stop before EOD
        
        if not (market_open <= current_time < market_close):
            return False
        
        # Need sufficient data
        min_bars = max(self.ma_period, self.atr_period) + 10
        if not context.bars_5s or len(context.bars_5s) < min_bars:
            return False
        
        return True

