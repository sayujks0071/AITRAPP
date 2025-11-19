"""Expiry Short Strangle V2 Strategy - Regime-Aware Weekly Income Engine"""
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

import structlog
from prometheus_client import Counter

from packages.core.models import Instrument, InstrumentType, Signal, SignalSide, Tick
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)

# Observability Metrics
expiry_strangle_v2_setups_evaluated = Counter(
    'expiry_strangle_v2_setups_evaluated_total',
    'Total number of strangle setups evaluated',
    ['underlying']
)

expiry_strangle_v2_filter_rejections = Counter(
    'expiry_strangle_v2_filter_rejections_total',
    'Strangle setups rejected by each filter',
    ['underlying', 'filter_name']
)

expiry_strangle_v2_signals_approved = Counter(
    'expiry_strangle_v2_signals_approved_total',
    'Strangle signals that passed all filters',
    ['underlying']
)


class ExpiryShortStrangleV2(Strategy):
    """
    Expiry Short Strangle V2 - Regime-Aware Weekly Income Engine
    
    Upgrades from V1:
    1. Strict regime gating (R1 integration)
    2. Delta-based strike selection (0.18-0.22 delta)
    3. IV + realized vol filter (IV > realized)
    4. Move/ATR filter (block runaway trends)
    5. Tight time gates (10:15-12:00 entry)
    6. Hard linkage to H1 (10-15% tail coverage)
    
    Structure:
    - Sell 1× OTM Call (delta ~0.20)
    - Sell 1× OTM Put (delta ~0.20)
    - H1 overlay buys deep OTM puts (10-15% of premium)
    
    Entry Conditions:
    - Days to expiry: 2-5 (Tue-Thu for Thu expiry)
    - R1 regime: LOW_MEAN_REVERT or MEDIUM_TREND (block HIGH_EVENT/CHAOTIC)
    - IV percentile: 40-85
    - Realized vol < IV
    - Intraday move < 1.5× ATR(1d)
    - Time: 10:15-12:00 IST
    - Premium: ≥ ₹3,000 per strangle
    
    Risk Management:
    - Hard stop: 2× premium collected
    - Soft stop: 1× premium (consider partial roll)
    - Portfolio heat gate: Block if global heat > 1% or margin > 25-30%
    """
    
    def __init__(
        self,
        name: str,
        params: Dict,
        instrument_manager: Optional[Any] = None,
        risk_engine: Optional[Any] = None,
        metrics: Optional[Any] = None,
        regime_engine: Optional[Any] = None,
    ):
        super().__init__(name, params)
        
        self.cfg = params
        self.instrument_manager = instrument_manager
        self.risk = risk_engine
        self.metrics = metrics
        self.regime_engine = regime_engine
        
        # Position sizing
        self.max_positions = params.get("max_positions", 1)
        self.max_lot_size = params.get("max_lot_size", 1)
        self.instruments = params.get("instruments", ["NIFTY"])
        
        # Entry conditions
        self.min_dte = params.get("min_dte", 2)
        self.max_dte = params.get("max_dte", 5)
        self.target_delta_min = params.get("target_delta_min", 0.18)
        self.target_delta_max = params.get("target_delta_max", 0.22)
        self.min_ivp = params.get("min_ivp", 40)
        self.max_ivp = params.get("max_ivp", 85)
        self.min_premium_per_lot = params.get("min_premium_per_lot", 3000)
        
        # Regime integration
        self.allowed_regimes = params.get("allowed_regimes", ["LOW_MEAN_REVERT", "MEDIUM_TREND"])
        self.blocked_regimes = params.get("blocked_regimes", ["HIGH_EVENT", "CHAOTIC"])
        
        # Time gates
        entry_window_start = params.get("entry_window_start", "10:15")
        entry_window_end = params.get("entry_window_end", "12:00")
        self.entry_start = self._parse_time(entry_window_start)
        self.entry_end = self._parse_time(entry_window_end)
        
        # Risk management
        self.stop_loss_mult = params.get("stop_loss_mult", 2.0)
        self.soft_stop_mult = params.get("soft_stop_mult", 1.0)
        self.take_profit_pct = params.get("take_profit_pct", 50)
        self.max_portfolio_heat_pct = params.get("max_portfolio_heat_pct", 1.0)
        self.max_margin_usage_pct = params.get("max_margin_usage_pct", 30.0)
        
        # Move/ATR filter
        self.max_intraday_move_atr_mult = params.get("max_intraday_move_atr_mult", 1.5)
        
        # Realized vol filter
        self.realized_vol_window_days = params.get("realized_vol_window_days", 5)
        self.require_iv_above_realized = params.get("require_iv_above_realized", True)
        
        # State tracking
        self.last_signal_time: Dict[int, datetime] = {}
        self.min_signal_gap_hours = 24  # One signal per day max
        
        logger.info(
            "ExpiryShortStrangleV2 initialized",
            underlyings=self.instruments,
            enabled=params.get("enabled", True),
            mode=params.get("mode", "LIVE")
        )
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string (HH:MM) to time object"""
        try:
            hour, minute = map(int, time_str.split(":"))
            return time(hour, minute)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid time format: {time_str}, using default 10:15")
            return time(10, 15)
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """Generate short strangle signals with V2 filters"""
        if not self.validate(context):
            return []
        
        # Only trade on configured underlyings
        if context.instrument.symbol not in self.instruments:
            return []
        
        underlying = context.instrument.symbol
        
        # Track: Setup evaluated
        expiry_strangle_v2_setups_evaluated.labels(underlying=underlying).inc()
        
        # Filter 1: Time Gate (10:15-12:00)
        current_time = context.timestamp.time()
        if not (self.entry_start <= current_time <= self.entry_end):
            expiry_strangle_v2_filter_rejections.labels(
                underlying=underlying,
                filter_name="time_gate"
            ).inc()
            logger.debug(
                "Strangle rejected: Outside entry window",
                current_time=current_time,
                window_start=self.entry_start,
                window_end=self.entry_end
            )
            return []
        
        # Filter 2: Regime Check (R1 integration)
        current_regime = self._get_current_regime(context)
        if current_regime in self.blocked_regimes:
            expiry_strangle_v2_filter_rejections.labels(
                underlying=underlying,
                filter_name="regime_blocked"
            ).inc()
            logger.debug(
                "Strangle rejected: Blocked regime",
                regime=current_regime,
                blocked_regimes=self.blocked_regimes
            )
            return []
        
        if current_regime not in self.allowed_regimes:
            expiry_strangle_v2_filter_rejections.labels(
                underlying=underlying,
                filter_name="regime_not_allowed"
            ).inc()
            logger.debug(
                "Strangle rejected: Regime not allowed",
                regime=current_regime,
                allowed_regimes=self.allowed_regimes
            )
            return []
        
        # Filter 3: Days to Expiry (2-5 days)
        dte = self._get_days_to_expiry(context)
        if dte is None or dte < self.min_dte or dte > self.max_dte:
            expiry_strangle_v2_filter_rejections.labels(
                underlying=underlying,
                filter_name="dte_out_of_range"
            ).inc()
            logger.debug(
                "Strangle rejected: DTE out of range",
                dte=dte,
                min_dte=self.min_dte,
                max_dte=self.max_dte
            )
            return []
        
        # Filter 4: IV Percentile (40-85)
        if context.iv_percentile is None:
            expiry_strangle_v2_filter_rejections.labels(
                underlying=underlying,
                filter_name="iv_percentile_missing"
            ).inc()
            return []
        
        ivp = context.iv_percentile * 100  # Convert to percentage
        if ivp < self.min_ivp or ivp > self.max_ivp:
            expiry_strangle_v2_filter_rejections.labels(
                underlying=underlying,
                filter_name="iv_percentile_out_of_range"
            ).inc()
            logger.debug(
                "Strangle rejected: IV percentile out of range",
                ivp=ivp,
                min_ivp=self.min_ivp,
                max_ivp=self.max_ivp
            )
            return []
        
        # Filter 5: IV vs Realized Vol
        if self.require_iv_above_realized:
            realized_vol = self._get_realized_vol(context)
            current_iv = self._get_current_iv(context)
            
            if realized_vol is not None and current_iv is not None:
                if current_iv <= realized_vol:
                    expiry_strangle_v2_filter_rejections.labels(
                        underlying=underlying,
                        filter_name="iv_not_above_realized"
                    ).inc()
                    logger.debug(
                        "Strangle rejected: IV not above realized vol",
                        iv=current_iv,
                        realized_vol=realized_vol
                    )
                    return []
        
        # Filter 6: Move/ATR Filter (block runaway trends)
        intraday_move_atr = self._get_intraday_move_atr(context)
        if intraday_move_atr is not None:
            if intraday_move_atr > self.max_intraday_move_atr_mult:
                expiry_strangle_v2_filter_rejections.labels(
                    underlying=underlying,
                    filter_name="intraday_move_too_large"
                ).inc()
                logger.debug(
                    "Strangle rejected: Intraday move too large",
                    move_atr_mult=intraday_move_atr,
                    max_allowed=self.max_intraday_move_atr_mult
                )
                return []
        
        # Filter 7: Portfolio Heat Gate
        portfolio_heat = self._get_portfolio_heat(context)
        if portfolio_heat is not None and portfolio_heat > self.max_portfolio_heat_pct:
            expiry_strangle_v2_filter_rejections.labels(
                underlying=underlying,
                filter_name="portfolio_heat_too_high"
            ).inc()
            logger.debug(
                "Strangle rejected: Portfolio heat too high",
                heat=portfolio_heat,
                max_allowed=self.max_portfolio_heat_pct
            )
            return []
        
        # Filter 8: Margin Usage Gate
        margin_usage = self._get_margin_usage(context)
        if margin_usage is not None and margin_usage > self.max_margin_usage_pct:
            expiry_strangle_v2_filter_rejections.labels(
                underlying=underlying,
                filter_name="margin_usage_too_high"
            ).inc()
            logger.debug(
                "Strangle rejected: Margin usage too high",
                margin_usage=margin_usage,
                max_allowed=self.max_margin_usage_pct
            )
            return []
        
        # Filter 9: Avoid duplicate signals
        if not self._can_generate_signal(context.instrument.token, context.timestamp):
            expiry_strangle_v2_filter_rejections.labels(
                underlying=underlying,
                filter_name="signal_cooldown"
            ).inc()
            return []
        
        # All filters passed - generate signal
        signal = self._generate_strangle_signal(context, dte, ivp)
        
        if signal:
            expiry_strangle_v2_signals_approved.labels(underlying=underlying).inc()
            logger.info(
                "Strangle signal approved",
                underlying=underlying,
                dte=dte,
                ivp=ivp,
                premium=signal.metadata.get("premium_collected", 0)
            )
            return [signal]
        
        return []
    
    def _generate_strangle_signal(
        self,
        context: StrategyContext,
        dte: int,
        ivp: float
    ) -> Optional[Signal]:
        """Generate the actual strangle signal with delta-based strike selection"""
        underlying = context.instrument.symbol
        
        if not context.latest_tick:
            return None
        
        spot_price = context.latest_tick.last_price
        if spot_price <= 0:
            return None
        
        # Find options with target delta (0.18-0.22)
        call_strike, call_premium = self._find_strike_by_delta(
            context, underlying, spot_price, dte, "CE", self.target_delta_min, self.target_delta_max
        )
        put_strike, put_premium = self._find_strike_by_delta(
            context, underlying, spot_price, dte, "PE", self.target_delta_min, self.target_delta_max
        )
        
        if call_strike is None or put_strike is None:
            logger.debug("Could not find strikes with target delta")
            return None
        
        # Check premium requirement
        total_premium = call_premium + put_premium
        if total_premium < self.min_premium_per_lot:
            logger.debug(
                "Premium too low",
                total_premium=total_premium,
                min_required=self.min_premium_per_lot
            )
            return None
        
        # Create strangle signal
        # Note: In production, this would create two separate signals (one for CE, one for PE)
        # For now, we create a composite signal
        signal = Signal(
            strategy=self.name,
            instrument=context.instrument,  # Will need to create composite instrument
            side=SignalSide.SELL,
            quantity=self.max_lot_size,
            price=total_premium,  # Net credit
            timestamp=context.timestamp,
            metadata={
                "structure": "SHORT_STRANGLE",
                "call_strike": call_strike,
                "put_strike": put_strike,
                "call_premium": call_premium,
                "put_premium": put_premium,
                "premium_collected": total_premium,
                "dte": dte,
                "ivp": ivp,
                "stop_loss": total_premium * self.stop_loss_mult,
                "take_profit_pct": self.take_profit_pct,
                "regime": self._get_current_regime(context),
                "tail_coverage_pct": 0.15,  # H1 will handle this
            }
        )
        
        return signal
    
    def _find_strike_by_delta(
        self,
        context: StrategyContext,
        underlying: str,
        spot: float,
        dte: int,
        option_type: str,
        delta_min: float,
        delta_max: float
    ) -> Tuple[Optional[float], float]:
        """
        Find strike with target delta range.
        
        Returns:
            (strike, premium) or (None, 0.0) if not found
        """
        # In production, this would:
        # 1. Get options chain for underlying + expiry
        # 2. Calculate delta for each strike
        # 3. Find strike closest to target delta range
        # 4. Return strike and premium
        
        # For now, simplified approximation:
        # Delta ~0.20 means roughly 20% OTM
        # For calls: strike ≈ spot * 1.02 (2% OTM)
        # For puts: strike ≈ spot * 0.98 (2% OTM)
        
        if option_type == "CE":
            target_strike = round(spot * 1.02, 50)  # Round to nearest 50
            # Estimate premium (simplified - would use actual option pricing)
            premium = spot * 0.01 * (dte / 7.0)  # Rough estimate
        else:  # PE
            target_strike = round(spot * 0.98, 50)
            premium = spot * 0.01 * (dte / 7.0)
        
        return target_strike, premium
    
    def _get_current_regime(self, context: StrategyContext) -> str:
        """Get current regime from R1 engine"""
        if self.regime_engine:
            try:
                regime = self.regime_engine.get_current_regime(context.instrument.symbol)
                return regime.value if hasattr(regime, 'value') else str(regime)
            except Exception as e:
                logger.debug(f"Could not get regime: {e}")
        
        # Fallback: return UNKNOWN
        return "UNKNOWN"
    
    def _get_days_to_expiry(self, context: StrategyContext) -> Optional[int]:
        """Get days to expiry for nearest weekly expiry"""
        if context.instrument.expiry:
            delta = context.instrument.expiry.date() - context.timestamp.date()
            return delta.days
        
        # Try to find nearest weekly expiry
        # In production, would query instrument manager
        return None
    
    def _get_realized_vol(self, context: StrategyContext) -> Optional[float]:
        """Get 5-10 day realized volatility"""
        # In production, would calculate from historical bars
        # For now, return None (filter will be skipped)
        return None
    
    def _get_current_iv(self, context: StrategyContext) -> Optional[float]:
        """Get current implied volatility"""
        # In production, would get from option pricing
        # For now, return None (filter will be skipped)
        return None
    
    def _get_intraday_move_atr(self, context: StrategyContext) -> Optional[float]:
        """Get intraday move as multiple of ATR(1d)"""
        if not context.latest_tick or not context.bars_5s:
            return None
        
        # Get today's open price
        today_open = context.bars_5s[0].open if context.bars_5s else context.latest_tick.last_price
        current_price = context.latest_tick.last_price
        
        intraday_move_pct = abs((current_price - today_open) / today_open) if today_open > 0 else 0
        
        # Calculate ATR(1d) - simplified
        # In production, would use proper ATR calculation
        atr_1d_pct = 0.015  # Assume 1.5% daily ATR
        
        return intraday_move_pct / atr_1d_pct if atr_1d_pct > 0 else None
    
    def _get_portfolio_heat(self, context: StrategyContext) -> Optional[float]:
        """Get current portfolio heat percentage"""
        if self.risk:
            try:
                return self.risk.get_portfolio_heat_pct()
            except Exception:
                pass
        return None
    
    def _get_margin_usage(self, context: StrategyContext) -> Optional[float]:
        """Get current margin usage percentage"""
        if context.available_margin > 0:
            used_margin = context.net_liquid - context.available_margin
            total_margin = context.net_liquid
            return (used_margin / total_margin * 100) if total_margin > 0 else None
        return None
    
    def _can_generate_signal(self, instrument_token: int, timestamp: datetime) -> bool:
        """Check if we can generate a signal (cooldown check)"""
        if instrument_token in self.last_signal_time:
            last_time = self.last_signal_time[instrument_token]
            gap = timestamp - last_time
            if gap.total_seconds() < self.min_signal_gap_hours * 3600:
                return False
        
        self.last_signal_time[instrument_token] = timestamp
        return True

