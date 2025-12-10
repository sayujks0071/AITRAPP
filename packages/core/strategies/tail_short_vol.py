"""Tail-Hedged Short Vol Overlay (H1) - Automatic tail hedge coverage for short vol strategies"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from packages.core.models import Instrument, InstrumentType, Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


@dataclass
class TailState:
    """State for tail hedge management per underlying"""
    last_short_notional: float = 0.0
    last_tail_notional: float = 0.0
    last_rebalance_time: Optional[datetime] = None


class TailShortVolOverlay(Strategy):
    """
    Tail-Hedged Short Vol Overlay (H1)
    
    This is NOT a trading strategy - it's a risk overlay that:
    1. Watches all short-premium strategies
    2. Estimates net short premium notional
    3. Ensures minimum tail hedge coverage in deep OTM puts
    4. Tops up/rolls hedges when needed
    
    Works automatically to protect short vol exposure.
    """
    
    def __init__(
        self,
        name: str,
        params: Dict[str, Any],
        instrument_manager: Optional[Any] = None,
        risk_engine: Optional[Any] = None,
        metrics: Optional[Any] = None,
        positions_store: Optional[Any] = None,
    ):
        super().__init__(name, params)
        
        self.cfg = params
        self.short_strats = set(params.get("short_vol_strategies", []))
        self.tail_underlyings = params.get("tail_underlyings", [])
        self.tail_instr_cfg = params.get("tail_instruments", {})
        self.risk_budgets = params.get("risk_budgets", {})
        self.rebalance_cfg = params.get("rebalance", {})
        self.tail_exit_cfg = params.get("tail_exit", {})
        self.regime_overlays = params.get("regime_overlays", {})
        
        self.instrument_manager = instrument_manager
        self.risk = risk_engine
        self.metrics = metrics
        self.positions_store = positions_store  # For accessing current positions
        
        # State per underlying
        self.state: Dict[str, TailState] = {}
        
        logger.info(
            "TailShortVolOverlay initialized",
            short_vol_strategies=list(self.short_strats),
            tail_underlyings=self.tail_underlyings,
            enabled=params.get("enabled", True)
        )
    
    def _get_state(self, underlying: str) -> TailState:
        """Get or create state for underlying"""
        if underlying not in self.state:
            self.state[underlying] = TailState()
        return self.state[underlying]
    
    def _current_regime_multiplier(self, regime: Optional[str]) -> float:
        """Get coverage multiplier for current regime"""
        if not regime:
            return 1.0
        overlay = self.regime_overlays.get(regime, {})
        return overlay.get("coverage_multiplier", 1.0)
    
    def _aggregate_short_premium_notional(
        self,
        context: StrategyContext,
        strategies: set,
        underlying: str
    ) -> float:
        """
        Aggregate short premium notional across short-vol strategies.
        
        Uses position store as canonical source.
        """
        if not self.positions_store:
            return 0.0
        
        try:
            if hasattr(self.positions_store, 'aggregate_short_premium_notional'):
                return self.positions_store.aggregate_short_premium_notional(
                    strategies=strategies,
                    underlying=underlying
                )
            return 0.0
        except Exception as e:
            logger.error("Error aggregating short premium", underlying=underlying, error=str(e))
            return 0.0
    
    def _aggregate_tail_hedge_notional(
        self,
        context: StrategyContext,
        underlying: str
    ) -> float:
        """
        Aggregate current tail hedge notional (deep OTM puts).
        
        Uses position store as canonical source.
        """
        if not self.positions_store:
            return 0.0
        
        try:
            if hasattr(self.positions_store, 'aggregate_tail_hedge_notional'):
                return self.positions_store.aggregate_tail_hedge_notional(
                    underlying=underlying,
                    tail_type="DEEP_OTM_PUT"
                )
            return 0.0
        except Exception as e:
            logger.error("Error aggregating tail hedge", underlying=underlying, error=str(e))
            return 0.0
    
    def _select_tail_expiry(
        self,
        underlying: str,
        max_days: int = 20
    ) -> Optional[datetime]:
        """Select expiry for tail puts"""
        if not self.instrument_manager:
            return None
        
        try:
            now = datetime.now()
            all_options = [
                inst for inst in self.instrument_manager._instruments.values()
                if inst.symbol == underlying
                and inst.is_option
                and inst.exchange == "NFO"
                and inst.expiry
                and inst.instrument_type == InstrumentType.PE
            ]
            
            if not all_options:
                return None
            
            # Get next monthly expiry (or nearest with enough days)
            expiries = sorted(set(opt.expiry for opt in all_options if opt.expiry))
            
            for expiry in expiries:
                days_to_expiry = (expiry - now).days
                if days_to_expiry >= max_days:
                    return expiry
            
            # Fallback to furthest expiry
            return expiries[-1] if expiries else None
        except Exception as e:
            logger.error("Error selecting tail expiry", underlying=underlying, error=str(e))
            return None
    
    def _select_deep_otm_put_strike(
        self,
        underlying: str,
        spot: float,
        expiry: datetime,
        strike_offset_pct: float
    ) -> Optional[float]:
        """Select deep OTM put strike"""
        if not self.instrument_manager:
            return None
        
        try:
            # Get all puts for this expiry
            expiry_options = [
                inst for inst in self.instrument_manager._instruments.values()
                if inst.symbol == underlying
                and inst.is_option
                and inst.exchange == "NFO"
                and inst.expiry == expiry
                and inst.instrument_type == InstrumentType.PE
            ]
            
            if not expiry_options:
                return None
            
            # Calculate target strike (OTM by offset_pct)
            target_strike = spot * (1.0 - strike_offset_pct / 100.0)
            
            # Find closest strike below target
            strikes = sorted(set(opt.strike for opt in expiry_options if opt.strike))
            if not strikes:
                return None
            
            # Find strike closest to target (but below)
            closest_strike = min(strikes, key=lambda s: abs(s - target_strike))
            
            # Ensure it's OTM (below spot)
            if closest_strike >= spot:
                # Get next lower strike
                lower_strikes = [s for s in strikes if s < spot]
                if lower_strikes:
                    closest_strike = max(lower_strikes)
                else:
                    return None
            
            return closest_strike
        except Exception as e:
            logger.error("Error selecting tail strike", underlying=underlying, error=str(e))
            return None
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """
        Called periodically to check and adjust tail hedge coverage.
        
        This overlay monitors short vol exposure and ensures tail coverage.
        """
        if not self.cfg.get("enabled", True):
            return []
        
        underlying = context.instrument.symbol
        if underlying not in self.tail_underlyings:
            return []
        
        # Check rebalance interval
        state = self._get_state(underlying)
        now = context.timestamp
        
        if state.last_rebalance_time:
            interval_minutes = self.rebalance_cfg.get("interval_minutes", 30)
            elapsed_minutes = (now - state.last_rebalance_time).total_seconds() / 60
            if elapsed_minutes < interval_minutes:
                return []
        
        # Get current regime
        regime = None
        if hasattr(context, 'features') and context.features:
            regime = context.features.get("regime")
        
        # Aggregate short premium notional
        short_notional = self._aggregate_short_premium_notional(
            context,
            self.short_strats,
            underlying
        )
        
        # Aggregate tail hedge notional
        tail_notional = self._aggregate_tail_hedge_notional(context, underlying)
        
        # Record metrics
        if self.metrics:
            labels = {"underlying": underlying}
            self.metrics.gauge("tail_short_vol_short_notional", labels).set(short_notional)
            self.metrics.gauge("tail_short_vol_tail_notional", labels).set(tail_notional)
        
        # If almost no short exposure, do nothing
        if short_notional <= 0.0:
            return []
        
        # Calculate coverage
        coverage_pct = (tail_notional / short_notional) * 100.0 if short_notional > 0 else 0.0
        
        if self.metrics:
            labels = {"underlying": underlying}
            self.metrics.gauge("tail_short_vol_coverage_pct", labels).set(coverage_pct)
        
        # Target coverage adjusted by regime and event context
        base_target = self.risk_budgets.get("target_tail_coverage_pct", 0.15)
        regime_mult = self._current_regime_multiplier(regime)
        
        # Get event multiplier from E1 (if available)
        event_mult = 1.0
        if hasattr(context, 'get_tag'):
            event_day_type = context.get_tag("event_day_type")
            if event_day_type and hasattr(context, 'get_global_event_context'):
                event_ctx = context.get_global_event_context()
                if event_ctx:
                    event_mult = event_ctx.h1_coverage_multiplier
        
        target_coverage_pct = base_target * regime_mult * event_mult * 100.0
        
        min_cov = self.risk_budgets.get("min_tail_coverage_pct", 0.10) * regime_mult * 100.0
        max_cov = self.risk_budgets.get("max_tail_coverage_pct", 0.25) * regime_mult * 100.0
        
        target_coverage_pct = max(min_cov, min(target_coverage_pct, max_cov))
        
        # Check if coverage gap is significant
        gap = target_coverage_pct - coverage_pct
        min_gap = self.rebalance_cfg.get("min_tail_gap_pct", 3.0)
        
        if abs(gap) < min_gap:
            return []
        
        # Check max short premium cap
        max_short_premium_pct = self.risk_budgets.get("max_short_premium_pct", 0.40)
        # Would need total capital - for now, skip this check
        # In production, would check: (short_notional / total_capital) * 100.0
        
        # Calculate desired tail notional
        desired_tail_notional = short_notional * (target_coverage_pct / 100.0)
        additional_tail = max(0.0, desired_tail_notional - tail_notional)
        
        # Check minimum change threshold
        min_change = short_notional * (self.rebalance_cfg.get("min_notional_change_pct", 10.0) / 100.0)
        if additional_tail < min_change:
            return []
        
        # Build tail adjustment trade
        signal = self._build_tail_adjustment_signal(context, underlying, additional_tail)
        
        if not signal:
            return []
        
        # Risk check
        if self.risk and hasattr(self.risk, 'can_allocate'):
            max_cap = self.risk_budgets.get("max_tail_coverage_pct", 0.25)
            if not self.risk.can_allocate(signal, max_capital_pct=max_cap):
                return []
        
        # Update state
        state.last_short_notional = short_notional
        state.last_tail_notional = tail_notional + additional_tail
        state.last_rebalance_time = now
        
        if self.metrics:
            labels = {"underlying": underlying}
            self.metrics.counter("tail_short_vol_adjustments", labels).inc()
        
        logger.info(
            "Tail hedge adjustment",
            underlying=underlying,
            short_notional=short_notional,
            tail_notional=tail_notional,
            coverage_pct=coverage_pct,
            target_coverage_pct=target_coverage_pct,
            additional_tail=additional_tail,
            regime=regime
        )
        
        return [signal]
    
    def _build_tail_adjustment_signal(
        self,
        context: StrategyContext,
        underlying: str,
        additional_tail_notional: float
    ) -> Optional[Signal]:
        """Build signal to buy deep OTM puts for tail hedge"""
        spot = context.latest_tick.last_price if context.latest_tick else 0.0
        if spot <= 0:
            return None
        
        # Select expiry
        max_days = self.tail_exit_cfg.get("max_days_to_expiry", 20)
        expiry = self._select_tail_expiry(underlying, max_days)
        if not expiry:
            logger.debug("Could not find tail expiry", underlying=underlying)
            return None
        
        # Select strike
        strike_offset_pct = self.tail_instr_cfg.get("strike_offset_pct", 5.0)
        strike = self._select_deep_otm_put_strike(underlying, spot, expiry, strike_offset_pct)
        if not strike:
            logger.debug("Could not find tail strike", underlying=underlying)
            return None
        
        # Get option instrument
        if not self.instrument_manager:
            return None
        
        tail_option = None
        for inst in self.instrument_manager._instruments.values():
            if (inst.symbol == underlying
                and inst.is_option
                and inst.exchange == "NFO"
                and inst.expiry == expiry
                and inst.strike == strike
                and inst.instrument_type == InstrumentType.PE):
                tail_option = inst
                break
        
        if not tail_option:
            logger.debug("Could not find tail option", underlying=underlying, strike=strike, expiry=expiry)
            return None
        
        # Estimate option price (would use market data in production)
        # For now, use rough estimate
        opt_price = context.latest_tick.mid if context.latest_tick else spot * 0.01  # Placeholder
        
        # Calculate lots needed
        lot_size = tail_option.lot_size
        if opt_price <= 0:
            return None
        
        lots = int(additional_tail_notional / (opt_price * lot_size))
        if lots <= 0:
            return None
        
        # Create signal
        signal = Signal(
            strategy_name=self.name,
            timestamp=context.timestamp,
            instrument=tail_option,
            side=SignalSide.LONG,  # Buy puts
            entry_price=opt_price,
            stop_loss=opt_price * 0.5,  # Placeholder
            confidence=0.9,
            rationale=f"Tail hedge: Buy {lots} lots of {tail_option.tradingsymbol} for {additional_tail_notional:.0f} notional",
            features={
                "tail_short_vol": True,
                "entry_type": "tail_hedge",
                "underlying": underlying,
                "strike": strike,
                "expiry": expiry.isoformat(),
                "lots": lots,
                "notional": additional_tail_notional,
            }
        )
        
        return signal

