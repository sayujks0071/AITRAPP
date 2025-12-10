"""Term-Structure / Calendar Vol Arb (T1) - Exploit IV differences between weekly and monthly expiries"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Any, Dict, List, Optional

import structlog

from packages.core.models import Instrument, InstrumentType, Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


@dataclass
class CalendarBookState:
    """Tracks current calendar book (per underlying)"""
    is_open: bool = False
    entry_time: Optional[datetime] = None
    weekly_expiry: Optional[datetime] = None
    monthly_expiry: Optional[datetime] = None
    atm_call_weekly_token: Optional[int] = None
    atm_call_monthly_token: Optional[int] = None
    atm_call_weekly_symbol: Optional[str] = None
    atm_call_monthly_symbol: Optional[str] = None
    atm_put_weekly_token: Optional[int] = None
    atm_put_monthly_token: Optional[int] = None
    atm_put_weekly_symbol: Optional[str] = None
    atm_put_monthly_symbol: Optional[str] = None
    lots: int = 0
    accumulated_pnl: float = 0.0


class CalendarArb(Strategy):
    """
    Term-Structure / Calendar Volatility Arbitrage (T1)
    
    Strategy:
    1. Monitor IV difference between weekly and monthly expiries
    2. When weekly IV >> monthly IV: Long calendar (sell weekly, buy monthly)
    3. Profit from IV convergence or time decay of weekly leg
    4. Exit based on time, PnL, or expiry proximity
    
    Works best when term structure is distorted (events, panic, etc.)
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
        self.exit_cfg = params.get("exits", {})
        self.risk_cfg = params.get("risk", {})
        self.integration_cfg = params.get("integration", {})
        
        self.instrument_manager = instrument_manager
        self.risk = risk_engine
        self.metrics = metrics
        
        # In-memory state per underlying
        self.state: Dict[str, CalendarBookState] = {}
        
        logger.info(
            "CalendarArb initialized",
            underlyings=params.get("underlyings", []),
            enabled=params.get("enabled", True),
            mode=params.get("mode", "PAPER")
        )
    
    def _get_state(self, underlying: str) -> CalendarBookState:
        """Get or create state for underlying"""
        if underlying not in self.state:
            self.state[underlying] = CalendarBookState()
        return self.state[underlying]
    
    def _in_entry_window(self, now: datetime) -> bool:
        """Check if current time is in entry window"""
        entry_window = self.entry_cfg.get("entry_window", {})
        start_str = entry_window.get("start", "09:30")
        end_str = entry_window.get("end", "13:30")
        
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
    
    def _compute_iv_from_option(self, instrument: Instrument, spot: float) -> float:
        """
        Compute implied volatility from option price (simplified).
        
        In production, use proper Black-Scholes inversion or fetch from market data.
        For now, use a placeholder based on moneyness and time to expiry.
        """
        if not instrument.strike or not instrument.expiry:
            return 0.0
        
        # Placeholder: would need actual option price and Black-Scholes inversion
        # For now, return a reasonable estimate based on context
        # In production, fetch IV from market data or compute from option price
        
        # Simplified: assume IV is around 20-30% for ATM options
        days_to_expiry = (instrument.expiry - datetime.now()).days if instrument.expiry else 1
        moneyness = spot / instrument.strike if instrument.strike > 0 else 1.0
        
        # Rough IV estimate (would be replaced with real calculation)
        base_iv = 0.25  # 25% base IV
        if abs(moneyness - 1.0) < 0.05:  # ATM
            return base_iv
        else:
            # OTM options have lower IV typically
            return base_iv * 0.9
        
        # TODO: Replace with proper IV calculation or market data fetch
    
    def _select_expiry(
        self,
        underlying: str,
        expiry_type: str = "weekly",
        min_days: int = 0,
        max_days: int = 30
    ) -> Optional[datetime]:
        """
        Select nearest weekly or monthly expiry.
        
        Args:
            underlying: Underlying symbol
            expiry_type: "weekly" or "monthly"
            min_days: Minimum days to expiry
            max_days: Maximum days to expiry
        
        Returns:
            Expiry datetime or None
        """
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
            ]
            
            if not all_options:
                return None
            
            # Filter by expiry window
            valid_expiries = []
            for opt in all_options:
                days_to_expiry = (opt.expiry - now).days
                if min_days <= days_to_expiry <= max_days:
                    valid_expiries.append(opt.expiry)
            
            if not valid_expiries:
                return None
            
            # Get unique expiries sorted
            unique_expiries = sorted(set(valid_expiries))
            
            if expiry_type == "weekly":
                # Nearest weekly (typically 0-7 days)
                for exp in unique_expiries:
                    days = (exp - now).days
                    if 0 <= days <= 7:
                        return exp
                # Fallback to nearest
                return unique_expiries[0] if unique_expiries else None
            elif expiry_type == "monthly":
                # Nearest monthly (typically 7-30 days)
                for exp in unique_expiries:
                    days = (exp - now).days
                    if 7 < days <= 30:
                        return exp
                # Fallback to furthest within range
                for exp in reversed(unique_expiries):
                    days = (exp - now).days
                    if days <= 30:
                        return exp
                return None
            
            return None
        except Exception as e:
            logger.error("Error selecting expiry", underlying=underlying, expiry_type=expiry_type, error=str(e))
            return None
    
    def _select_atm_option(
        self,
        underlying: str,
        spot: float,
        expiry: datetime,
        right: str = "C"
    ) -> Optional[Instrument]:
        """Select ATM option for given expiry and type"""
        if not self.instrument_manager:
            return None
        
        try:
            # Get options for this expiry
            expiry_options = [
                inst for inst in self.instrument_manager._instruments.values()
                if inst.symbol == underlying
                and inst.is_option
                and inst.exchange == "NFO"
                and inst.expiry == expiry
                and inst.instrument_type == (InstrumentType.CE if right == "C" else InstrumentType.PE)
            ]
            
            if not expiry_options:
                return None
            
            # Find ATM strike (closest to spot)
            strikes = sorted(set(opt.strike for opt in expiry_options if opt.strike))
            if not strikes:
                return None
            
            atm_strike = min(strikes, key=lambda s: abs(s - spot))
            
            # Get option at ATM strike
            atm_option = next(
                (opt for opt in expiry_options if opt.strike == atm_strike),
                None
            )
            
            return atm_option
        except Exception as e:
            logger.error("Error selecting ATM option", underlying=underlying, expiry=expiry, right=right, error=str(e))
            return None
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """Generate signals: open calendar or exit"""
        if not self.cfg.get("enabled", True):
            return []
        
        underlying = context.instrument.symbol
        if underlying not in self.cfg.get("underlyings", []):
            return []
        
        state = self._get_state(underlying)
        signals: List[Signal] = []
        
        # Check max open calendars per underlying
        if state.is_open:
            # Already have a calendar, check exit
            exit_signal = self._maybe_exit_calendar(context, state)
            if exit_signal:
                signals.append(exit_signal)
        else:
            # Check if we can open a new calendar
            max_open = self.risk_cfg.get("max_open_calendars_per_underlying", 2)
            # For now, we only track one calendar per underlying
            # In production, you'd track a list and check count
            open_signal = self._maybe_open_calendar(context, state)
            if open_signal:
                signals.append(open_signal)
        
        return signals
    
    def _maybe_open_calendar(self, context: StrategyContext, state: CalendarBookState) -> Optional[Signal]:
        """Check if we should open a long calendar spread"""
        now = context.timestamp
        
        # Entry window check
        if not self._in_entry_window(now):
            return None
        
        # R1 regime check
        if not self._r1_regime_allows(context):
            logger.debug("R1 regime does not allow calendar arb entry", underlying=context.instrument.symbol)
            return None
        
        # Get spot
        spot = context.latest_tick.last_price if context.latest_tick else 0.0
        if spot <= 0:
            return None
        
        # Select expiries
        weekly_expiry = self._select_expiry(context.instrument.symbol, "weekly", min_days=0, max_days=7)
        monthly_expiry = self._select_expiry(context.instrument.symbol, "monthly", min_days=7, max_days=30)
        
        if not weekly_expiry or not monthly_expiry:
            logger.debug("Could not find weekly/monthly expiries", underlying=context.instrument.symbol)
            return None
        
        # Check minimum days between expiries
        days_between = (monthly_expiry - weekly_expiry).days
        min_days = self.entry_cfg.get("min_days_between_expiries", 5)
        if days_between < min_days:
            logger.debug("Expiries too close", underlying=context.instrument.symbol, days_between=days_between)
            return None
        
        # Get ATM options
        call_weekly = self._select_atm_option(context.instrument.symbol, spot, weekly_expiry, "C")
        call_monthly = self._select_atm_option(context.instrument.symbol, spot, monthly_expiry, "C")
        put_weekly = self._select_atm_option(context.instrument.symbol, spot, weekly_expiry, "P")
        put_monthly = self._select_atm_option(context.instrument.symbol, spot, monthly_expiry, "P")
        
        if not call_weekly or not call_monthly:
            logger.debug("Could not find ATM options", underlying=context.instrument.symbol)
            return None
        
        # Compute IVs
        iv_call_weekly = self._compute_iv_from_option(call_weekly, spot)
        iv_call_monthly = self._compute_iv_from_option(call_monthly, spot)
        iv_put_weekly = self._compute_iv_from_option(put_weekly, spot) if put_weekly else iv_call_weekly
        iv_put_monthly = self._compute_iv_from_option(put_monthly, spot) if put_monthly else iv_call_monthly
        
        # Average call/put IV
        iv_weekly = (iv_call_weekly + iv_put_weekly) / 2.0
        iv_monthly = (iv_call_monthly + iv_put_monthly) / 2.0
        
        if iv_monthly <= 0.0 or iv_weekly <= 0.0:
            return None
        
        # Compute term structure metrics
        term_ratio = iv_weekly / iv_monthly if iv_monthly > 0 else 0.0
        term_spread = iv_weekly - iv_monthly
        
        # Record metrics
        if self.metrics:
            labels = {"underlying": context.instrument.symbol}
            self.metrics.gauge("calendar_arb_iv_weekly", labels).set(iv_weekly)
            self.metrics.gauge("calendar_arb_iv_monthly", labels).set(iv_monthly)
            self.metrics.gauge("calendar_arb_term_ratio", labels).set(term_ratio)
            self.metrics.gauge("calendar_arb_term_spread", labels).set(term_spread)
        
        # Check long calendar conditions (per-underlying bands override global)
        bands_cfg = self.entry_cfg.get("term_bands", {}).get(context.instrument.symbol, {})
        ratio_min = bands_cfg.get(
            "term_ratio_long_cal_min",
            self.entry_cfg.get("term_ratio_long_cal_min", 1.20),
        )
        spread_min = bands_cfg.get(
            "term_spread_long_cal_min",
            self.entry_cfg.get("term_spread_long_cal_min", 0.05),
        )
        
        if not (term_ratio >= ratio_min and term_spread >= spread_min):
            logger.debug(
                "Term structure not favorable",
                underlying=context.instrument.symbol,
                term_ratio=term_ratio,
                term_spread=term_spread
            )
            return None
        
        # IV rank check (simplified - use context IV percentile)
        iv_percentile = context.iv_percentile or 50.0
        iv_rank = iv_percentile / 100.0
        
        min_iv_rank = self.entry_cfg.get("min_iv_rank_monthly", 0.20)
        max_iv_rank = self.entry_cfg.get("max_iv_rank_monthly", 0.85)
        
        if iv_rank < min_iv_rank or iv_rank > max_iv_rank:
            logger.debug("IV rank out of range", underlying=context.instrument.symbol, iv_rank=iv_rank)
            return None
        
        # Liquidity checks (simplified)
        if context.latest_tick:
            spread_pct = context.latest_tick.spread_pct
            if spread_pct > self.entry_cfg.get("max_bid_ask_spread_pct", 0.80):
                return None
        
        # Structure sizing
        base_lots = self.entry_cfg.get("base_lots_per_underlying", 1)
        lots = base_lots
        
        # Scale by extreme term ratio
        extreme_ratio = self.entry_cfg.get("term_ratio_extreme", 1.40)
        if term_ratio >= extreme_ratio:
            max_lots = self.entry_cfg.get("max_lots_per_underlying", 3)
            lots = min(max_lots, base_lots * 2)
        
        # Create signal for long calendar
        # Long calendar: sell weekly, buy monthly
        # For now, create signal for the call side (in production, would be multi-leg)
        signal = Signal(
            strategy_name=self.name,
            timestamp=now,
            instrument=call_weekly,  # Primary instrument (weekly call to sell)
            side=SignalSide.SHORT,  # Sell weekly
            entry_price=spot,
            stop_loss=spot * 0.98,  # Placeholder
            take_profit_1=spot * 1.02,  # Placeholder
            confidence=0.7,
            rationale=f"Calendar arb: Long calendar (sell weekly {call_weekly.tradingsymbol}, buy monthly {call_monthly.tradingsymbol})",
            features={
                "calendar_arb": True,
                "entry_type": "long_calendar",
                "weekly_expiry": weekly_expiry.isoformat(),
                "monthly_expiry": monthly_expiry.isoformat(),
                "call_weekly_symbol": call_weekly.tradingsymbol,
                "call_monthly_symbol": call_monthly.tradingsymbol,
                "put_weekly_symbol": put_weekly.tradingsymbol if put_weekly else None,
                "put_monthly_symbol": put_monthly.tradingsymbol if put_monthly else None,
                "lots": lots,
                "term_ratio": term_ratio,
                "term_spread": term_spread,
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
        state.weekly_expiry = weekly_expiry
        state.monthly_expiry = monthly_expiry
        state.atm_call_weekly_token = call_weekly.token
        state.atm_call_monthly_token = call_monthly.token
        state.atm_call_weekly_symbol = call_weekly.tradingsymbol
        state.atm_call_monthly_symbol = call_monthly.tradingsymbol
        if put_weekly:
            state.atm_put_weekly_token = put_weekly.token
            state.atm_put_weekly_symbol = put_weekly.tradingsymbol
        if put_monthly:
            state.atm_put_monthly_token = put_monthly.token
            state.atm_put_monthly_symbol = put_monthly.tradingsymbol
        state.lots = lots
        
        if self.metrics:
            labels = {"underlying": context.instrument.symbol}
            self.metrics.counter("calendar_arb_books_opened", labels).inc()
        
        logger.info(
            "Calendar arb book opened",
            underlying=context.instrument.symbol,
            weekly_expiry=weekly_expiry.isoformat(),
            monthly_expiry=monthly_expiry.isoformat(),
            call_weekly=call_weekly.tradingsymbol,
            call_monthly=call_monthly.tradingsymbol,
            term_ratio=term_ratio,
            term_spread=term_spread,
            lots=lots
        )
        
        return signal
    
    def _maybe_exit_calendar(self, context: StrategyContext, state: CalendarBookState) -> Optional[Signal]:
        """Check if we should exit the calendar book"""
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
            max_hold_days = self.exit_cfg.get("max_hold_days", 3)
            elapsed_days = (now - state.entry_time).days
            if elapsed_days >= max_hold_days:
                return self._build_close_signal(context, state, "max_hold_days")
        
        # Decay/expiry proximity exit
        if state.weekly_expiry:
            days_to_weekly = (state.weekly_expiry - now).days
            decay_exit_days = self.exit_cfg.get("decay_exit_days", 1)
            if days_to_weekly <= decay_exit_days:
                return self._build_close_signal(context, state, "decay_exit")
        
        # PnL-based exits (would use position store in production)
        # For now, skip PnL checks (would need position tracking)
        # In production, would call:
        # book_pnl = self.positions_store.book_pnl_for_strategy(self.name, "calendar_arb")
        # capital_used = self.positions_store.capital_used_for_strategy(self.name, "calendar_arb")
        
        return None
    
    def _build_close_signal(
        self,
        context: StrategyContext,
        state: CalendarBookState,
        reason: str
    ) -> Signal:
        """Build signal to close calendar positions"""
        # Get weekly call as primary instrument
        close_instrument = None
        if state.atm_call_weekly_token and self.instrument_manager:
            close_instrument = self.instrument_manager.get_instrument(state.atm_call_weekly_token)
        
        if not close_instrument:
            close_instrument = context.instrument
        
        signal = Signal(
            strategy_name=self.name,
            timestamp=context.timestamp,
            instrument=close_instrument,
            side=SignalSide.FLAT,  # Close all
            entry_price=context.latest_tick.last_price if context.latest_tick else 0.0,
            stop_loss=0.0,
            confidence=1.0,
            rationale=f"Calendar arb exit: {reason}",
            features={
                "calendar_arb": True,
                "entry_type": "close_calendar",
                "exit_reason": reason,
                "weekly_expiry": state.weekly_expiry.isoformat() if state.weekly_expiry else None,
                "monthly_expiry": state.monthly_expiry.isoformat() if state.monthly_expiry else None,
            }
        )
        
        # Reset state
        state.is_open = False
        state.lots = 0
        
        if self.metrics:
            labels = {"underlying": context.instrument.symbol, "reason": reason}
            self.metrics.counter("calendar_arb_books_closed", labels).inc()
        
        logger.info(
            "Calendar arb book closed",
            underlying=context.instrument.symbol,
            reason=reason,
            weekly_expiry=state.weekly_expiry.isoformat() if state.weekly_expiry else None,
            monthly_expiry=state.monthly_expiry.isoformat() if state.monthly_expiry else None
        )
        
        return signal
