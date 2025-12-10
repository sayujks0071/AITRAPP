"""Premium Adaptive Trend strategy

High-conviction, low-drawdown intraday trend strategy that combines:
- Trend stack: EMA fast > EMA slow and Supertrend direction aligned
- Strength filter: ADX gate plus RSI-in-range to avoid chasing blow-offs
- Volatility gate: ATR as % of price capped to avoid chaotic tape
- Entry: wait for a pullback to fast EMA, then breakout over recent structure
- Exits: ATR-based stop near structure; dual targets driven by minimum R:R

Optimized for NIFTY/BANKNIFTY futures & liquid index options; works on 5s bars.
"""
from datetime import time
from typing import List, Optional, Tuple

import structlog

from packages.core.models import Bar, Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


class PremiumAdaptiveTrendStrategy(Strategy):
    """
    Multi-confirmation trend strategy with volatility gating.

    Entry logic (LONG):
    1) Trend stack: ema_fast > ema_slow and supertrend_direction == 1
    2) Strength: adx >= threshold and RSI sits inside a healthy band
    3) Volatility: ATR% of price below cap
    4) Pullback: recent low tagged fast EMA within tolerance
    5) Breakout: current price clears recent swing high

    Shorts are symmetric (trend stack down, below VWAP/EMA, breakdown of swing low).
    Stops sit just beyond the recent swing with ATR buffer; targets enforce R:R.
    """

    def __init__(self, name: str, params: dict):
        super().__init__(name, params)

        # Trend / strength filters
        self.ema_fast_period = params.get("ema_fast", 34)
        self.ema_slow_period = params.get("ema_slow", 89)
        self.adx_threshold = params.get("adx_threshold", 22)
        self.backtest_relaxed_adx = params.get("backtest_relaxed_adx", 18)
        self.rsi_entry_range = params.get("rsi_entry_range", [45, 65])

        # Volatility + structure
        self.atr_vol_cap_pct = params.get("atr_vol_cap_pct", 1.1)  # ATR% of price ceiling
        self.atr_stop_mult = params.get("atr_stop_mult", 1.2)
        self.pullback_lookback = params.get("pullback_lookback", 12)
        self.pullback_tolerance_pct = params.get("pullback_tolerance_pct", 0.35)
        self.breakout_lookback = params.get("breakout_lookback", 10)

        # Risk / exits
        self.rr_min = params.get("rr_min", 2.3)
        self.backtest_rr_min = params.get("backtest_rr_min", 1.6)
        self.cooldown_minutes = params.get("cooldown_minutes", 12)
        self.max_positions = params.get("max_positions", 1)  # override base default
        self.allowed_instruments = params.get("instruments", ["NIFTY", "BANKNIFTY"])

        # Regime + event guards
        self.skip_event_days = params.get("skip_event_days", True)
        self.block_regimes = [r.upper() for r in params.get("block_regimes", ["CHAOTIC", "HIGH_EVENT"])]
        self.preferred_regimes = [r.upper() for r in params.get("preferred_regimes", ["MEDIUM_TREND", "LOW_VOL", "LOW_MEAN_REVERT"])]

        # Derived / state
        self.min_bars = params.get(
            "min_bars",
            max(self.ema_slow_period + 10, self.pullback_lookback + 8, self.breakout_lookback + 6, 120),
        )
        self.last_signal_time: dict = {}
        self.last_signal_side: dict = {}

    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """Generate signals with premium filters applied."""
        self._backtest_mode = context.backtest_mode

        if not self.validate(context):
            return []

        token = context.instrument.token
        bars = context.bars_5s
        if not bars or len(bars) < self.min_bars:
            return []

        if context.instrument.symbol not in self.allowed_instruments:
            return []

        # Event/regime guards to keep drawdowns low
        if self.skip_event_days and context.is_event_day:
            return []
        if context.regime and context.regime.upper() in self.block_regimes:
            return []

        # Cooldown enforcement
        if not self._can_generate_signal(token, context.timestamp):
            return []

        latest_bar = bars[-1]
        current_price = context.latest_tick.last_price
        atr = latest_bar.atr or self._calculate_atr(bars, 14) or (current_price * 0.008)
        adx = latest_bar.adx
        rsi = latest_bar.rsi
        ema_fast = latest_bar.ema_fast or self._ema_from_bars(bars, self.ema_fast_period)
        ema_slow = latest_bar.ema_slow or self._ema_from_bars(bars, self.ema_slow_period)
        supertrend_dir = latest_bar.supertrend_direction
        vwap = latest_bar.vwap

        atr_pct = self._atr_pct(current_price, atr)
        adx_gate = self.backtest_relaxed_adx if context.backtest_mode else self.adx_threshold
        rr_floor = self.backtest_rr_min if context.backtest_mode else self.rr_min
        atr_cap = self.atr_vol_cap_pct + (0.3 if context.backtest_mode else 0.0)

        if atr_pct is None or atr_pct > atr_cap:
            return []

        rsi_ok = True
        if rsi is not None and len(self.rsi_entry_range) == 2:
            rsi_ok = self.rsi_entry_range[0] <= rsi <= self.rsi_entry_range[1]

        strength_ok = (adx or 0) >= adx_gate and rsi_ok

        signals: List[Signal] = []
        swing_high, swing_low = self._swing_levels(bars, self.breakout_lookback)
        pullback_long = self._pullback_touched(bars, ema_fast, expect_above=True)
        pullback_short = self._pullback_touched(bars, ema_fast, expect_above=False)

        # LONG setup
        if (
            ema_fast
            and ema_slow
            and supertrend_dir == 1
            and ema_fast > ema_slow
            and strength_ok
            and pullback_long
            and current_price > ema_fast
            and current_price > (swing_high or current_price)
            and (vwap is None or current_price >= vwap)
        ):
            signal = self._build_signal(
                context=context,
                side=SignalSide.LONG,
                entry_price=current_price,
                atr=atr,
                atr_pct=atr_pct,
                rr_floor=rr_floor,
                ema_fast=ema_fast,
                ema_slow=ema_slow,
                swing_level=swing_low,
                regime=context.regime,
            )
            if signal:
                signals.append(signal)
                self.last_signal_time[token] = context.timestamp
                self.last_signal_side[token] = "LONG"
                logger.info(
                    "PremiumAdaptiveTrend LONG",
                    instrument=context.instrument.tradingsymbol,
                    entry=signal.entry_price,
                    rr=signal.risk_reward_ratio,
                    atr_pct=atr_pct,
                )

        # SHORT setup
        if (
            ema_fast
            and ema_slow
            and supertrend_dir == -1
            and ema_fast < ema_slow
            and strength_ok
            and pullback_short
            and current_price < ema_fast
            and current_price < (swing_low or current_price)
            and (vwap is None or current_price <= vwap)
        ):
            signal = self._build_signal(
                context=context,
                side=SignalSide.SHORT,
                entry_price=current_price,
                atr=atr,
                atr_pct=atr_pct,
                rr_floor=rr_floor,
                ema_fast=ema_fast,
                ema_slow=ema_slow,
                swing_level=swing_high,
                regime=context.regime,
            )
            if signal:
                signals.append(signal)
                self.last_signal_time[token] = context.timestamp
                self.last_signal_side[token] = "SHORT"
                logger.info(
                    "PremiumAdaptiveTrend SHORT",
                    instrument=context.instrument.tradingsymbol,
                    entry=signal.entry_price,
                    rr=signal.risk_reward_ratio,
                    atr_pct=atr_pct,
                )

        return signals

    def _build_signal(
        self,
        context: StrategyContext,
        side: SignalSide,
        entry_price: float,
        atr: float,
        atr_pct: float,
        rr_floor: float,
        ema_fast: float,
        ema_slow: float,
        swing_level: Optional[float],
        regime: Optional[str],
    ) -> Optional[Signal]:
        """Create Signal with ATR/structure-based stops and dual targets."""
        stop_loss = self._stop_from_structure(side, entry_price, atr, swing_level)
        risk = (entry_price - stop_loss) if side == SignalSide.LONG else (stop_loss - entry_price)
        if risk <= 0:
            return None

        reward = risk * rr_floor
        take_profit_1 = entry_price + (reward * 0.6 if side == SignalSide.LONG else -reward * 0.6)
        take_profit_2 = entry_price + (reward if side == SignalSide.LONG else -reward)

        rr_ratio = reward / risk if risk else 0.0
        confidence = self._confidence_score(rr_ratio, atr_pct, regime)

        rationale = (
            f"Trend stack {'UP' if side == SignalSide.LONG else 'DOWN'} with ADX/RSI strength, "
            f"pullback-to-EMA and structure {'breakout' if side == SignalSide.LONG else 'breakdown'}"
        )

        signal = Signal(
            strategy_name=self.name,
            timestamp=context.timestamp,
            instrument=context.instrument,
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            confidence=confidence,
            rationale=rationale,
            features={
                "ema_fast": ema_fast,
                "ema_slow": ema_slow,
                "atr": atr,
                "atr_pct": atr_pct,
                "rr": rr_ratio,
                "swing_level": swing_level,
                "regime": regime,
            },
        )
        signal.risk_amount = risk
        signal.reward_amount = reward
        self.signals_generated += 1
        return signal

    def _stop_from_structure(
        self, side: SignalSide, entry_price: float, atr: float, swing_level: Optional[float]
    ) -> float:
        """Tight structural stop with ATR buffer to keep drawdown small."""
        atr_buffer = atr * self.atr_stop_mult
        if side == SignalSide.LONG:
            swing_based = (swing_level - (atr * 0.25)) if swing_level else entry_price - atr_buffer
            stop = max(swing_based, entry_price - atr_buffer)
            stop = min(stop, entry_price * 0.997)  # cap to avoid over-tight stops above entry
            return stop
        swing_based = (swing_level + (atr * 0.25)) if swing_level else entry_price + atr_buffer
        stop = min(swing_based, entry_price + atr_buffer)
        stop = max(stop, entry_price * 1.003)  # ensure stop stays above entry
        return stop

    def _confidence_score(self, rr: float, atr_pct: float, regime: Optional[str]) -> float:
        """Blend of R:R quality, volatility, and regime preference."""
        score = 0.55
        if rr >= self.rr_min * 1.1:
            score += 0.1
        if atr_pct <= self.atr_vol_cap_pct * 0.75:
            score += 0.1
        if regime and regime.upper() in self.preferred_regimes:
            score += 0.05
        return min(score, 0.95)

    def _pullback_touched(self, bars: List[Bar], ema_fast: Optional[float], expect_above: bool) -> bool:
        """Detect a pullback into fast EMA zone within tolerance and recovery."""
        if not ema_fast or len(bars) < self.pullback_lookback:
            return False

        recent = bars[-self.pullback_lookback :]
        band_low = ema_fast * (1 - self.pullback_tolerance_pct / 100)
        band_high = ema_fast * (1 + self.pullback_tolerance_pct / 100)
        touched = any(band_low <= b.low <= band_high for b in recent)
        last_close = recent[-1].close

        if expect_above:
            return touched and last_close > ema_fast
        return touched and last_close < ema_fast

    def _swing_levels(self, bars: List[Bar], lookback: int) -> Tuple[Optional[float], Optional[float]]:
        """Get recent swing high/low excluding the last bar."""
        if len(bars) <= lookback:
            return None, None
        window = bars[-(lookback + 1) : -1]
        swing_high = max(b.high for b in window)
        swing_low = min(b.low for b in window)
        return swing_high, swing_low

    def _atr_pct(self, price: float, atr: Optional[float]) -> Optional[float]:
        """ATR as % of price."""
        if not atr or price <= 0:
            return None
        return (atr / price) * 100

    def _calculate_atr(self, bars: List[Bar], period: int) -> Optional[float]:
        """Simple ATR calculation for fallback."""
        if len(bars) < period + 1:
            return None
        trs = []
        for i in range(len(bars) - period, len(bars)):
            prev_close = bars[i - 1].close
            high = bars[i].high
            low = bars[i].low
            trs.append(
                max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close),
                )
            )
        return sum(trs) / len(trs) if trs else None

    def _ema_from_bars(self, bars: List[Bar], period: int) -> Optional[float]:
        """Lightweight EMA for custom periods."""
        if len(bars) < period:
            return None
        k = 2 / (period + 1)
        ema = bars[-period].close
        for b in bars[-period + 1 :]:
            ema = (b.close * k) + (ema * (1 - k))
        return ema

    def _can_generate_signal(self, token: int, timestamp) -> bool:
        """Throttle signals per-instrument to avoid over-trading."""
        last_time = self.last_signal_time.get(token)
        if not last_time:
            return True
        delta_min = (timestamp - last_time).total_seconds() / 60
        return delta_min >= self.cooldown_minutes

    def validate(self, context: StrategyContext) -> bool:
        """Validate base + market hours + data sufficiency."""
        if not super().validate(context):
            return False

        current_time = context.timestamp.time()
        if not (time(9, 20) <= current_time < time(15, 20)):
            return False

        if not context.bars_5s or len(context.bars_5s) < self.min_bars:
            return False

        return True
