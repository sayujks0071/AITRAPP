"""Delta-Hedged Gamma Scalper (G1) - Long gamma via ATM straddles, delta-hedged with futures"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional

import math
import structlog

from packages.core.models import Instrument, InstrumentType, Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


@dataclass
class GammaBookState:
    """Tracks current gamma book (per underlying)"""
    is_open: bool = False
    entry_time: Optional[datetime] = None
    lots: int = 0
    atm_call_token: Optional[int] = None
    atm_put_token: Optional[int] = None
    atm_call_symbol: Optional[str] = None
    atm_put_symbol: Optional[str] = None
    futures_token: Optional[int] = None
    futures_symbol: Optional[str] = None
    rebalance_count: int = 0
    accumulated_pnl: float = 0.0
    last_rebalance_time: Optional[datetime] = None
    entry_spot: float = 0.0


@dataclass
class OptionGreeks:
    """Option Greeks (Black-Scholes-style approximation)"""
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    iv: float = 0.0


class GammaScalper(Strategy):
    """
    Delta-Hedged Gamma Scalper (G1)
    
    Strategy:
    1. Buy ATM straddle (long gamma)
    2. Delta hedge with futures to keep |Δ| ≈ 0
    3. Rebalance when delta drifts
    4. Exit based on time, PnL, or vol collapse
    
    Works best in MEDIUM_TREND or HIGH_EVENT regimes.
    """
    
    def __init__(
        self,
        name: str,
        params: Dict[str, Any],
        instrument_manager: Optional[Any] = None,
        risk_engine: Optional[Any] = None,
        metrics: Optional[Any] = None,
    ):
        super().__init__(name, params)
        
        self.cfg = params
        self.entry_cfg = params.get("entry", {})
        self.hedge_cfg = params.get("hedging", {})
        self.exit_cfg = params.get("exits", {})
        self.risk_cfg = params.get("risk", {})
        self.integration_cfg = params.get("integration", {})
        
        self.instrument_manager = instrument_manager
        self.risk = risk_engine
        self.metrics = metrics
        
        # In-memory state per underlying
        self.state: Dict[str, GammaBookState] = {}
        
        logger.info(
            "GammaScalper initialized",
            underlyings=params.get("underlyings", []),
            enabled=params.get("enabled", True),
            mode=params.get("mode", "PAPER")
        )
    
    def _get_state(self, underlying: str) -> GammaBookState:
        """Get or create state for underlying"""
        if underlying not in self.state:
            self.state[underlying] = GammaBookState()
        return self.state[underlying]
    
    def _in_entry_window(self, now: datetime) -> bool:
        """Check if current time is in entry window"""
        entry_window = self.entry_cfg.get("entry_window", {})
        start_str = entry_window.get("start", "09:20")
        end_str = entry_window.get("end", "11:00")
        
        try:
            start_time = time.fromisoformat(start_str)
            end_time = time.fromisoformat(end_str)
            current_time = now.time()
            return start_time <= current_time <= end_time
        except:
            return False
    
    def _r1_regime_allows(self, context: StrategyContext) -> bool:
        """Check if R1 regime allows trading"""
        if not self.integration_cfg.get("require_r1_regime", False):
            return True
        
        allowed = set(self.integration_cfg.get("allowed_r1_regimes", []))
        
        # Get regime from signal features or context
        regime = None
        if hasattr(context, 'features') and context.features:
            regime = context.features.get("regime")
        elif hasattr(context, 'iv_percentile'):
            # Fallback: estimate from IV (simplified)
            pass
        
        return regime in allowed if regime else True  # Default allow if can't determine
    
    def _estimate_iv(self, iv_percentile: Optional[float]) -> float:
        """
        Estimate IV level from percentile when broker IV is not wired in.
        Maps percentile [0,100] to a reasonable range [12%, 35%].
        """
        if iv_percentile is None:
            return 0.22
        p = max(0.0, min(100.0, iv_percentile)) / 100.0
        return 0.12 + p * (0.35 - 0.12)
    
    def _compute_greeks(
        self,
        instrument: Instrument,
        spot: float,
        days_to_expiry: float,
        iv_percentile: Optional[float] = None,
    ) -> OptionGreeks:
        """
        Compute option Greeks using a light-weight Black-Scholes approximation.
        """
        if not instrument.strike or not instrument.expiry or spot <= 0:
            return OptionGreeks()
        
        strike = float(instrument.strike)
        is_call = instrument.instrument_type == InstrumentType.CE
        
        # Time to expiry in years
        if days_to_expiry <= 0:
            days_to_expiry = 0.01
        t = days_to_expiry / 365.0
        
        # Risk-free rate (can be tuned via config)
        r = float(self.hedge_cfg.get("risk_free_rate", 0.06))
        
        # Volatility from percentile
        sigma = self._estimate_iv(iv_percentile)
        sigma = max(0.05, min(0.80, sigma))
        
        try:
            ln_fk = math.log(spot / strike)
        except ValueError:
            ln_fk = 0.0
        
        denom = sigma * math.sqrt(t)
        if denom <= 0:
            return OptionGreeks()
        
        d1 = (ln_fk + (r + 0.5 * sigma * sigma) * t) / denom
        d2 = d1 - denom
        
        def norm_cdf(x: float) -> float:
            return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
        
        def norm_pdf(x: float) -> float:
            return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)
        
        Nd1 = norm_cdf(d1)
        Nd2 = norm_cdf(d2)
        nd1 = norm_pdf(d1)
        
        # Delta
        if is_call:
            delta = Nd1
        else:
            delta = Nd1 - 1.0
        
        # Gamma (per underlying unit)
        gamma = nd1 / (spot * sigma * math.sqrt(t))
        
        # Theta per day (approximate)
        theta = (
            -(spot * nd1 * sigma) / (2.0 * math.sqrt(t))
            - r * strike * math.exp(-r * t) * Nd2
        ) / 365.0
        
        # Vega per 1 vol point
        vega = spot * nd1 * math.sqrt(t) / 100.0
        
        return OptionGreeks(
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            iv=sigma,
        )
    
    def _select_atm_options(
        self,
        underlying: str,
        spot: float,
        min_days: int = 1,
        max_days: int = 4
    ) -> Optional[tuple]:
        """
        Select ATM call and put for nearest weekly expiry.
        
        Returns: (call_instrument, put_instrument) or None
        """
        if not self.instrument_manager:
            return None
        
        # Get options chain
        try:
            # Find nearest weekly expiry
            now = datetime.now()
            all_options = [
                inst for inst in self.instrument_manager._instruments.values()
                if inst.symbol == underlying
                and inst.is_option
                and inst.exchange == "NFO"
                and inst.expiry
            ]
            
            if not all_options:
                return None
            
            # Filter by expiry window
            valid_options = []
            for opt in all_options:
                days_to_expiry = (opt.expiry - now).days
                if min_days <= days_to_expiry <= max_days:
                    valid_options.append(opt)
            
            if not valid_options:
                return None
            
            # Get nearest expiry
            expiries = sorted(set(opt.expiry for opt in valid_options))
            if not expiries:
                return None
            
            nearest_expiry = expiries[0]
            
            # Get options for this expiry
            expiry_options = [opt for opt in valid_options if opt.expiry == nearest_expiry]
            
            # Find ATM strike (closest to spot)
            strikes = sorted(set(opt.strike for opt in expiry_options if opt.strike))
            if not strikes:
                return None
            
            atm_strike = min(strikes, key=lambda s: abs(s - spot))
            
            # Get call and put at ATM strike
            call = next(
                (opt for opt in expiry_options
                 if opt.strike == atm_strike and opt.instrument_type == InstrumentType.CE),
                None
            )
            put = next(
                (opt for opt in expiry_options
                 if opt.strike == atm_strike and opt.instrument_type == InstrumentType.PE),
                None
            )
            
            if call and put:
                return (call, put)
            
            return None
        except Exception as e:
            logger.error("Error selecting ATM options", underlying=underlying, error=str(e))
            return None
    
    def _get_futures_contract(self, underlying: str) -> Optional[Instrument]:
        """Get futures contract for underlying"""
        if not self.instrument_manager:
            return None
        
        try:
            # Find nearest futures contract
            all_futures = [
                inst for inst in self.instrument_manager._instruments.values()
                if inst.symbol == underlying
                and inst.is_future
                and inst.exchange == "NFO"
                and inst.expiry
            ]
            
            if not all_futures:
                return None
            
            # Get nearest expiry
            now = datetime.now()
            nearest = min(
                all_futures,
                key=lambda f: abs((f.expiry - now).days) if f.expiry else 999
            )
            
            return nearest
        except Exception as e:
            logger.error("Error getting futures contract", underlying=underlying, error=str(e))
            return None
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """Generate signals: open book, hedge delta, or exit"""
        if not self.cfg.get("enabled", True):
            return []
        
        underlying = context.instrument.symbol
        if underlying not in self.cfg.get("underlyings", []):
            return []
        
        state = self._get_state(underlying)
        signals: List[Signal] = []
        
        # Three separate concerns: open, manage, exit
        if not state.is_open:
            signal = self._maybe_open_book(context, state)
            if signal:
                signals.append(signal)
        else:
            # Manage existing book: hedge + exit checks
            hedge_signal = self._maybe_hedge_delta(context, state)
            if hedge_signal:
                signals.append(hedge_signal)
            
            exit_signal = self._maybe_exit_book(context, state)
            if exit_signal:
                signals.append(exit_signal)
        
        return signals
    
    def _maybe_open_book(self, context: StrategyContext, state: GammaBookState) -> Optional[Signal]:
        """Check if we should open a new gamma book"""
        now = context.timestamp
        
        # Entry window check
        if not self._in_entry_window(now):
            return None
        
        # R1 regime check
        if not self._r1_regime_allows(context):
            logger.debug("R1 regime does not allow gamma scalper entry", underlying=context.instrument.symbol)
            return None
        
        # Basic filters
        spot = context.latest_tick.last_price if context.latest_tick else 0.0
        if spot <= 0:
            return None
        
        # IV rank check (simplified - use context IV percentile)
        iv_percentile = context.iv_percentile or 50.0
        iv_rank = iv_percentile / 100.0
        
        if iv_rank < self.entry_cfg.get("min_iv_rank", 0.20):
            return None
        if iv_rank > self.entry_cfg.get("max_iv_rank", 0.80):
            return None
        
        # RV/IV ratio check (simplified)
        # In production, compute from historical data
        rv_iv_min = self.entry_cfg.get("rv_iv_min", 0.9)
        # For now, assume it passes (would need realized vol calculation)
        
        # Liquidity check (simplified)
        if context.latest_tick:
            spread_pct = context.latest_tick.spread_pct
            if spread_pct > self.entry_cfg.get("max_bid_ask_spread_pct", 0.80):
                return None
        
        # Select ATM options
        options = self._select_atm_options(
            context.instrument.symbol,
            spot,
            min_days=self.entry_cfg.get("min_days_to_expiry", 1),
            max_days=self.entry_cfg.get("max_days_to_expiry", 4)
        )
        
        if not options:
            logger.debug("Could not find ATM options", underlying=context.instrument.symbol)
            return None
        
        call_instrument, put_instrument = options
        
        # Get futures for hedging
        futures = self._get_futures_contract(context.instrument.symbol)
        if not futures:
            logger.debug("Could not find futures contract", underlying=context.instrument.symbol)
            return None
        
        lots = self.entry_cfg.get("lots_per_underlying", 1)
        
        # Create signal for long straddle
        # Note: In production, you'd create a multi-leg order
        # For now, create a signal that represents the straddle
        signal = Signal(
            strategy_name=self.name,
            timestamp=now,
            instrument=call_instrument,  # Primary instrument (call)
            side=SignalSide.LONG,
            entry_price=spot,  # Approximate
            stop_loss=spot * 0.98,  # Placeholder
            take_profit_1=spot * 1.02,  # Placeholder
            confidence=0.7,
            rationale=f"Gamma scalper: Long ATM straddle {call_instrument.tradingsymbol} + {put_instrument.tradingsymbol}",
            features={
                "gamma_scalper": True,
                "entry_type": "straddle",
                "call_symbol": call_instrument.tradingsymbol,
                "put_symbol": put_instrument.tradingsymbol,
                "futures_symbol": futures.tradingsymbol,
                "lots": lots,
                "entry_spot": spot,
            }
        )
        
        # Risk check
        if self.risk and hasattr(self.risk, 'can_allocate'):
            max_capital_pct = self.risk_cfg.get("max_capital_pct", 0.05)
            if not self.risk.can_allocate(signal, max_capital_pct=max_capital_pct):
                return None
        
        # Update state
        state.is_open = True
        state.entry_time = now
        state.lots = lots
        state.atm_call_token = call_instrument.token
        state.atm_put_token = put_instrument.token
        state.atm_call_symbol = call_instrument.tradingsymbol
        state.atm_put_symbol = put_instrument.tradingsymbol
        state.futures_token = futures.token
        state.futures_symbol = futures.tradingsymbol
        state.rebalance_count = 0
        state.entry_spot = spot
        
        if self.metrics:
            labels = {"underlying": context.instrument.symbol}
            self.metrics.counter("gamma_scalper_books_opened", labels).inc()
        
        logger.info(
            "Gamma scalper book opened",
            underlying=context.instrument.symbol,
            call=call_instrument.tradingsymbol,
            put=put_instrument.tradingsymbol,
            futures=futures.tradingsymbol,
            lots=lots
        )
        
        return signal
    
    def _maybe_hedge_delta(self, context: StrategyContext, state: GammaBookState) -> Optional[Signal]:
        """Check if we need to hedge delta"""
        if not state.is_open:
            return None
        
        # Cooldown check
        if state.last_rebalance_time:
            cooldown_seconds = self.hedge_cfg.get("rebalance_cooldown_seconds", 60)
            elapsed = (context.timestamp - state.last_rebalance_time).total_seconds()
            if elapsed < cooldown_seconds:
                return None
        
        # Max rebalances check
        if state.rebalance_count >= self.risk_cfg.get("max_rebalances", 25):
            return None
        
        # Get current spot
        spot = context.latest_tick.last_price if context.latest_tick else state.entry_spot
        if spot <= 0:
            return None
        
        # Compute total delta
        # Get instruments
        if not self.instrument_manager:
            return None
        
        call_inst = self.instrument_manager.get_instrument(state.atm_call_token)
        put_inst = self.instrument_manager.get_instrument(state.atm_put_token)
        fut_inst = self.instrument_manager.get_instrument(state.futures_token)
        
        if not call_inst or not put_inst or not fut_inst:
            return None
        
        # Compute Greeks using Black-Scholes approximation
        days_to_expiry = (call_inst.expiry - context.timestamp).days if call_inst.expiry else 1
        iv_pct = getattr(context, "iv_percentile", None)
        call_greeks = self._compute_greeks(call_inst, spot, days_to_expiry, iv_pct)
        put_greeks = self._compute_greeks(put_inst, spot, days_to_expiry, iv_pct)
        
        # Total option delta
        option_delta = (call_greeks.delta + put_greeks.delta) * state.lots
        
        # Existing futures position delta (would need position tracking)
        # For now, assume 0 (would track in production)
        fut_pos_delta = 0.0
        
        total_delta = option_delta + fut_pos_delta
        abs_delta = abs(total_delta)
        
        # Record metrics
        if self.metrics:
            labels = {"underlying": context.instrument.symbol}
            self.metrics.gauge("gamma_scalper_abs_delta", labels).set(abs_delta)
        
        # Check if hedge needed
        threshold = self.hedge_cfg.get("rebalance_delta_threshold", 0.15)
        if abs_delta <= threshold:
            return None
        
        # Compute futures lots needed (delta ≈ lot_size per lot)
        fut_delta_per_lot = float(getattr(fut_inst, "lot_size", 1))
        lots_needed = -total_delta / fut_delta_per_lot
        lots_needed_rounded = int(round(lots_needed))
        
        if lots_needed_rounded == 0:
            return None
        
        # Cap hedge size
        max_lots = self.hedge_cfg.get("max_hedge_lots", 3)
        if abs(lots_needed_rounded) > max_lots:
            lots_needed_rounded = int(max_lots * (1 if lots_needed_rounded > 0 else -1))
        
        # Create hedge signal
        side = SignalSide.LONG if lots_needed_rounded > 0 else SignalSide.SHORT
        signal = Signal(
            strategy_name=self.name,
            timestamp=context.timestamp,
            instrument=fut_inst,
            side=side,
            entry_price=spot,
            stop_loss=spot * 0.99,  # Placeholder
            confidence=0.8,
            rationale=f"Gamma scalper delta hedge: {abs(lots_needed_rounded)} lots to offset {total_delta:.2f} delta",
            features={
                "gamma_scalper": True,
                "entry_type": "delta_hedge",
                "delta_offset": total_delta,
                "lots": abs(lots_needed_rounded),
            }
        )
        
        # Update state
        state.rebalance_count += 1
        state.last_rebalance_time = context.timestamp
        
        if self.metrics:
            labels = {"underlying": context.instrument.symbol}
            self.metrics.counter("gamma_scalper_rebalances", labels).inc()
        
        logger.debug(
            "Gamma scalper delta hedge",
            underlying=context.instrument.symbol,
            total_delta=total_delta,
            lots=lots_needed_rounded,
            rebalance_count=state.rebalance_count
        )
        
        return signal
    
    def _maybe_exit_book(self, context: StrategyContext, state: GammaBookState) -> Optional[Signal]:
        """Check if we should exit the gamma book"""
        if not state.is_open:
            return None
        
        now = context.timestamp
        time_str = now.strftime("%H:%M")
        
        # Time-based exit
        hard_exit_time = self.exit_cfg.get("hard_exit_time", "15:10")
        if time_str >= hard_exit_time:
            return self._build_close_signal(context, state, "time")
        
        # Hold-time safety
        if state.entry_time:
            max_hold_minutes = self.exit_cfg.get("max_hold_minutes", 300)
            elapsed_minutes = (now - state.entry_time).total_seconds() / 60
            if elapsed_minutes >= max_hold_minutes:
                return self._build_close_signal(context, state, "max_hold_time")
        
        # PnL-based exits (would use position store in production)
        # For now, skip PnL checks (would need position tracking)
        # In production, would call:
        # book_pnl = self.positions_store.book_pnl_for_strategy(self.name, "gamma_scalper")
        # capital_used = self.positions_store.capital_used_for_strategy(self.name, "gamma_scalper")
        
        # Vol collapse check (simplified)
        # Would need realized vol calculation
        
        return None
    
    def _build_close_signal(
        self,
        context: StrategyContext,
        state: GammaBookState,
        reason: str
    ) -> Signal:
        """Build signal to close all gamma scalper positions"""
        # Get futures instrument for the signal
        fut_inst = None
        if state.futures_token and self.instrument_manager:
            fut_inst = self.instrument_manager.get_instrument(state.futures_token)
        
        if not fut_inst:
            # Fallback to context instrument
            fut_inst = context.instrument
        
        signal = Signal(
            strategy_name=self.name,
            timestamp=context.timestamp,
            instrument=fut_inst,
            side=SignalSide.FLAT,  # Close all
            entry_price=context.latest_tick.last_price if context.latest_tick else 0.0,
            stop_loss=0.0,
            confidence=1.0,
            rationale=f"Gamma scalper exit: {reason}",
            features={
                "gamma_scalper": True,
                "entry_type": "close_all",
                "exit_reason": reason,
                "call_symbol": state.atm_call_symbol,
                "put_symbol": state.atm_put_symbol,
                "futures_symbol": state.futures_symbol,
            }
        )
        
        # Reset state
        state.is_open = False
        state.lots = 0
        state.rebalance_count = 0
        
        if self.metrics:
            labels = {"underlying": context.instrument.symbol, "reason": reason}
            self.metrics.counter("gamma_scalper_books_closed", labels).inc()
        
        logger.info(
            "Gamma scalper book closed",
            underlying=context.instrument.symbol,
            reason=reason,
            rebalance_count=state.rebalance_count
        )
        
        return signal
