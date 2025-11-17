"""Intraday Correlation / Dispersion Arbitrage (D1) - Index vs Sector volatility divergence"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any, Dict, List, Optional

import structlog

from packages.core.models import Instrument, InstrumentType, Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


@dataclass
class DispersionBookState:
    """Tracks current dispersion book (per pair)"""
    is_open: bool = False
    entry_time: Optional[datetime] = None
    parent: str = ""
    sector: str = ""
    lots_sector: int = 0
    lots_parent: int = 0
    parent_leg_symbols: Dict[str, str] = field(default_factory=dict)  # e.g. ce, pe short legs
    sector_leg_symbols: Dict[str, str] = field(default_factory=dict)  # e.g. ce, pe long legs
    accumulated_pnl: float = 0.0


class DispersionArb(Strategy):
    """
    Intraday Correlation / Dispersion Arbitrage (D1)
    
    Strategy:
    1. Monitor volatility divergence between parent (NIFTY) and sector (BANKNIFTY)
    2. When sector vol >> parent vol (dispersion):
       - Long vol in sector (long straddle)
       - Short vol in parent (short strangle)
    3. Exit when correlation breaks, vol normalizes, or PnL targets hit
    
    Works best when sector is hyperactive while parent stays calm.
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
        
        # State keyed by "parent|sector"
        self.state: Dict[str, DispersionBookState] = {}
        
        # Cache for price history (for correlation calculation)
        self._price_history: Dict[str, List[float]] = {}
        
        logger.info(
            "DispersionArb initialized",
            pairs=params.get("pairs", []),
            enabled=params.get("enabled", True),
            mode=params.get("mode", "PAPER")
        )
    
    def _pair_key(self, parent: str, sector: str) -> str:
        """Generate key for pair state"""
        return f"{parent}|{sector}"
    
    def _get_state(self, parent: str, sector: str) -> DispersionBookState:
        """Get or create state for pair"""
        key = self._pair_key(parent, sector)
        if key not in self.state:
            self.state[key] = DispersionBookState(parent=parent, sector=sector)
        return self.state[key]
    
    def _in_entry_window(self, now: datetime) -> bool:
        """Check if current time is in entry window"""
        entry_window = self.entry_cfg.get("entry_window", {})
        start_str = entry_window.get("start", "10:00")
        end_str = entry_window.get("end", "14:00")
        
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
    
    def _compute_realised_vol_intraday(self, context: StrategyContext, minutes: int) -> float:
        """
        Compute realized volatility over last N minutes.
        
        Uses 5-second bars if available, otherwise falls back to approximation.
        """
        if context.bars_5s and len(context.bars_5s) >= 2:
            # Calculate returns from bars
            bars_needed = max(2, minutes // 5)  # Approximate bars needed
            recent_bars = context.bars_5s[-bars_needed:] if len(context.bars_5s) > bars_needed else context.bars_5s
            
            if len(recent_bars) >= 2:
                closes = [b.close for b in recent_bars]
                returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
                if returns:
                    # Calculate standard deviation of returns
                    mean_return = sum(returns) / len(returns)
                    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
                    std_dev = variance ** 0.5
                    
                    # Annualize (assuming 252 trading days, ~78 5-min bars per day)
                    annualized_vol = std_dev * (252 * 78) ** 0.5
                    return annualized_vol
        
        # Fallback: use ATR if available
        if context.bars_5s and len(context.bars_5s) > 0:
            latest_bar = context.bars_5s[-1]
            if latest_bar.atr and latest_bar.close > 0:
                # Rough approximation: ATR as % of price, annualized
                atr_pct = (latest_bar.atr / latest_bar.close) * 100.0
                return atr_pct / 100.0 * (252 ** 0.5)  # Rough annualization
        
        return 0.20  # Default 20% annualized
    
    def _compute_correlation(
        self,
        parent_context: StrategyContext,
        sector_context: StrategyContext,
        minutes: int
    ) -> float:
        """
        Compute correlation between parent and sector returns over last N minutes.
        
        Uses price history cache to track both instruments.
        """
        # Update price history
        parent_symbol = parent_context.instrument.symbol
        sector_symbol = sector_context.instrument.symbol
        
        if parent_context.latest_tick:
            if parent_symbol not in self._price_history:
                self._price_history[parent_symbol] = []
            self._price_history[parent_symbol].append(parent_context.latest_tick.last_price)
            # Keep only last N prices (approximate)
            max_prices = max(100, minutes * 12)  # Assume ~12 prices per minute
            if len(self._price_history[parent_symbol]) > max_prices:
                self._price_history[parent_symbol] = self._price_history[parent_symbol][-max_prices:]
        
        if sector_context.latest_tick:
            if sector_symbol not in self._price_history:
                self._price_history[sector_symbol] = []
            self._price_history[sector_symbol].append(sector_context.latest_tick.last_price)
            max_prices = max(100, minutes * 12)
            if len(self._price_history[sector_symbol]) > max_prices:
                self._price_history[sector_symbol] = self._price_history[sector_symbol][-max_prices:]
        
        # Calculate correlation from price history
        parent_prices = self._price_history.get(parent_symbol, [])
        sector_prices = self._price_history.get(sector_symbol, [])
        
        if len(parent_prices) < 2 or len(sector_prices) < 2:
            return 0.7  # Default correlation
        
        # Align lengths
        min_len = min(len(parent_prices), len(sector_prices))
        parent_prices = parent_prices[-min_len:]
        sector_prices = sector_prices[-min_len:]
        
        # Calculate returns
        parent_returns = [(parent_prices[i] - parent_prices[i-1]) / parent_prices[i-1] 
                         for i in range(1, len(parent_prices))]
        sector_returns = [(sector_prices[i] - sector_prices[i-1]) / sector_prices[i-1] 
                         for i in range(1, len(sector_prices))]
        
        if len(parent_returns) < 2 or len(sector_returns) < 2:
            return 0.7
        
        # Calculate correlation
        mean_parent = sum(parent_returns) / len(parent_returns)
        mean_sector = sum(sector_returns) / len(sector_returns)
        
        numerator = sum((parent_returns[i] - mean_parent) * (sector_returns[i] - mean_sector) 
                       for i in range(len(parent_returns)))
        parent_var = sum((r - mean_parent) ** 2 for r in parent_returns)
        sector_var = sum((r - mean_sector) ** 2 for r in sector_returns)
        
        if parent_var > 0 and sector_var > 0:
            correlation = numerator / ((parent_var * sector_var) ** 0.5)
            return max(-1.0, min(1.0, correlation))  # Clamp to [-1, 1]
        
        return 0.7  # Default
    
    def _get_peer_context(self, symbol: str, current_context: StrategyContext) -> Optional[StrategyContext]:
        """
        Get context for peer instrument (sector or parent).
        
        In production, this would fetch from a shared context store.
        For now, we'll create a simplified context from instrument manager.
        """
        if not self.instrument_manager:
            return None
        
        try:
            # Find instrument by symbol
            peer_instrument = None
            for inst in self.instrument_manager._instruments.values():
                if inst.symbol == symbol and inst.exchange in ["NSE", "NFO"]:
                    # Prefer equity/index instrument
                    if inst.instrument_type == InstrumentType.EQ or not inst.is_option:
                        peer_instrument = inst
                        break
            
            if not peer_instrument:
                return None
            
            # Create simplified context (would be enhanced in production)
            # For now, reuse current context structure with peer instrument
            peer_context = StrategyContext(
                timestamp=current_context.timestamp,
                instrument=peer_instrument,
                latest_tick=current_context.latest_tick,  # Would fetch actual tick in production
                bars_5s=current_context.bars_5s,  # Would fetch actual bars in production
                iv_percentile=current_context.iv_percentile,  # Would compute for peer in production
            )
            
            return peer_context
        except Exception as e:
            logger.error("Error getting peer context", symbol=symbol, error=str(e))
            return None
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """Generate signals: open pair book or exit"""
        if not self.cfg.get("enabled", True):
            return []
        
        parent = context.instrument.symbol
        signals: List[Signal] = []
        
        # Find pairs where this is the parent
        for pair in self.cfg.get("pairs", []):
            if pair.get("parent") != parent:
                continue
            
            sector_name = pair.get("sector")
            if not sector_name:
                continue
            
            # Get sector context
            sector_context = self._get_peer_context(sector_name, context)
            if not sector_context:
                logger.debug("Could not get sector context", parent=parent, sector=sector_name)
                continue
            
            state = self._get_state(parent, sector_name)
            
            if not state.is_open:
                # Check if we can open a pair book
                signal = self._maybe_open_pair(context, sector_context, state)
                if signal:
                    signals.append(signal)
            else:
                # Check exit conditions
                exit_signal = self._maybe_exit_pair(context, sector_context, state)
                if exit_signal:
                    signals.append(exit_signal)
        
        return signals
    
    def _maybe_open_pair(
        self,
        parent_context: StrategyContext,
        sector_context: StrategyContext,
        state: DispersionBookState
    ) -> Optional[Signal]:
        """Check if we should open a dispersion pair book"""
        now = parent_context.timestamp
        
        # Entry window check
        if not self._in_entry_window(now):
            return None
        
        # R1 regime check
        if not self._r1_regime_allows(parent_context):
            logger.debug("R1 regime does not allow dispersion arb entry", parent=parent_context.instrument.symbol)
            return None
        
        # Compute realized vols
        rv_minutes = self.entry_cfg.get("rv_lookback_minutes", 60)
        rv_parent = self._compute_realised_vol_intraday(parent_context, rv_minutes)
        rv_sector = self._compute_realised_vol_intraday(sector_context, rv_minutes)
        
        if rv_parent <= 0 or rv_sector <= 0:
            return None
        
        vol_ratio = rv_sector / rv_parent if rv_parent > 0 else 0.0
        
        # Compute correlation
        corr_minutes = self.entry_cfg.get("corr_lookback_minutes", 60)
        corr = self._compute_correlation(parent_context, sector_context, corr_minutes)
        
        # Compute IVs (simplified - use context IV percentile)
        iv_parent = 0.15 + (parent_context.iv_percentile or 50.0) / 100.0 * 0.20 if parent_context.iv_percentile else 0.25
        iv_sector = 0.15 + (sector_context.iv_percentile or 50.0) / 100.0 * 0.20 if sector_context.iv_percentile else 0.25
        
        if iv_parent <= 0 or iv_sector <= 0:
            return None
        
        iv_ratio = iv_sector / iv_parent if iv_parent > 0 else 0.0
        
        # Record metrics
        if self.metrics:
            labels = {"parent": parent_context.instrument.symbol, "sector": sector_context.instrument.symbol}
            self.metrics.gauge("dispersion_arb_rv_parent", labels).set(rv_parent)
            self.metrics.gauge("dispersion_arb_rv_sector", labels).set(rv_sector)
            self.metrics.gauge("dispersion_arb_corr", labels).set(corr)
            self.metrics.gauge("dispersion_arb_iv_ratio", labels).set(iv_ratio)
            self.metrics.gauge("dispersion_arb_vol_ratio", labels).set(vol_ratio)
        
        # Check thresholds
        min_corr = self.entry_cfg.get("min_corr", 0.6)
        min_vol_ratio = self.entry_cfg.get("min_vol_ratio_sector_parent", 1.5)
        min_iv_ratio = self.entry_cfg.get("min_iv_ratio_sector_parent", 1.2)
        
        if corr < min_corr:
            logger.debug("Correlation too low", parent=parent_context.instrument.symbol, corr=corr)
            return None
        
        if vol_ratio < min_vol_ratio:
            logger.debug("Vol ratio too low", parent=parent_context.instrument.symbol, vol_ratio=vol_ratio)
            return None
        
        if iv_ratio < min_iv_ratio:
            logger.debug("IV ratio too low", parent=parent_context.instrument.symbol, iv_ratio=iv_ratio)
            return None
        
        # Liquidity checks (simplified)
        if parent_context.latest_tick and sector_context.latest_tick:
            parent_spread = parent_context.latest_tick.spread_pct
            sector_spread = sector_context.latest_tick.spread_pct
            max_spread = self.entry_cfg.get("max_bid_ask_spread_pct", 0.8)
            
            if parent_spread > max_spread or sector_spread > max_spread:
                return None
        
        # Get spot prices
        parent_spot = parent_context.latest_tick.last_price if parent_context.latest_tick else 0.0
        sector_spot = sector_context.latest_tick.last_price if sector_context.latest_tick else 0.0
        
        if parent_spot <= 0 or sector_spot <= 0:
            return None
        
        # Select options (simplified - would need proper option chain access)
        # For now, create a signal representing the pair trade
        lots_sector = self.entry_cfg.get("lots_sector_long_vol", 1)
        lots_parent = self.entry_cfg.get("lots_parent_short_vol", 1)
        
        # Create signal for the pair trade
        # In production, this would be a multi-leg order
        signal = Signal(
            strategy_name=self.name,
            timestamp=now,
            instrument=parent_context.instrument,  # Primary instrument (parent)
            side=SignalSide.LONG,  # Net long vol (sector long - parent short)
            entry_price=parent_spot,
            stop_loss=parent_spot * 0.98,  # Placeholder
            take_profit_1=parent_spot * 1.02,  # Placeholder
            confidence=0.7,
            rationale=f"Dispersion arb: Long vol {sector_context.instrument.symbol}, Short vol {parent_context.instrument.symbol}",
            features={
                "dispersion_arb": True,
                "entry_type": "pair_book",
                "parent": parent_context.instrument.symbol,
                "sector": sector_context.instrument.symbol,
                "lots_sector": lots_sector,
                "lots_parent": lots_parent,
                "vol_ratio": vol_ratio,
                "iv_ratio": iv_ratio,
                "correlation": corr,
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
        state.lots_sector = lots_sector
        state.lots_parent = lots_parent
        # In production, would store actual option symbols here
        
        if self.metrics:
            labels = {"parent": parent_context.instrument.symbol, "sector": sector_context.instrument.symbol}
            self.metrics.counter("dispersion_arb_books_opened", labels).inc()
        
        logger.info(
            "Dispersion arb book opened",
            parent=parent_context.instrument.symbol,
            sector=sector_context.instrument.symbol,
            vol_ratio=vol_ratio,
            iv_ratio=iv_ratio,
            correlation=corr,
            lots_sector=lots_sector,
            lots_parent=lots_parent
        )
        
        return signal
    
    def _maybe_exit_pair(
        self,
        parent_context: StrategyContext,
        sector_context: StrategyContext,
        state: DispersionBookState
    ) -> Optional[Signal]:
        """Check if we should exit the dispersion pair book"""
        if not state.is_open:
            return None
        
        now = parent_context.timestamp
        time_str = now.strftime("%H:%M")
        
        # Time-based exit
        hard_exit_time = self.exit_cfg.get("hard_exit_time", "15:10")
        if time_str >= hard_exit_time:
            return self._build_close_signal(parent_context, sector_context, state, "time")
        
        # Recompute dispersion metrics
        rv_minutes = self.entry_cfg.get("rv_lookback_minutes", 60)
        rv_parent = self._compute_realised_vol_intraday(parent_context, rv_minutes)
        rv_sector = self._compute_realised_vol_intraday(sector_context, rv_minutes)
        vol_ratio = rv_sector / rv_parent if rv_parent > 0 else 0.0
        
        corr_minutes = self.entry_cfg.get("corr_lookback_minutes", 60)
        corr = self._compute_correlation(parent_context, sector_context, corr_minutes)
        
        # PnL-based exits (would use position store in production)
        # For now, skip PnL checks (would need position tracking)
        # In production, would call:
        # book_pnl = self.positions_store.book_pnl_for_strategy(self.name, "dispersion_pair")
        # capital_used = self.positions_store.capital_used_for_strategy(self.name, "dispersion_pair")
        
        # Structural exits
        corr_break_min = self.exit_cfg.get("corr_break_min", 0.4)
        if corr < corr_break_min:
            return self._build_close_signal(parent_context, sector_context, state, "corr_break")
        
        vol_ratio_normalise_max = self.exit_cfg.get("vol_ratio_normalise_max", 1.2)
        if vol_ratio <= vol_ratio_normalise_max:
            return self._build_close_signal(parent_context, sector_context, state, "vol_normalise")
        
        return None
    
    def _build_close_signal(
        self,
        parent_context: StrategyContext,
        sector_context: StrategyContext,
        state: DispersionBookState,
        reason: str
    ) -> Signal:
        """Build signal to close dispersion pair positions"""
        signal = Signal(
            strategy_name=self.name,
            timestamp=parent_context.timestamp,
            instrument=parent_context.instrument,
            side=SignalSide.FLAT,  # Close all
            entry_price=parent_context.latest_tick.last_price if parent_context.latest_tick else 0.0,
            stop_loss=0.0,
            confidence=1.0,
            rationale=f"Dispersion arb exit: {reason}",
            features={
                "dispersion_arb": True,
                "entry_type": "close_pair",
                "exit_reason": reason,
                "parent": state.parent,
                "sector": state.sector,
            }
        )
        
        # Reset state
        state.is_open = False
        state.lots_parent = 0
        state.lots_sector = 0
        
        if self.metrics:
            labels = {"parent": state.parent, "sector": state.sector, "reason": reason}
            self.metrics.counter("dispersion_arb_books_closed", labels).inc()
        
        logger.info(
            "Dispersion arb book closed",
            parent=state.parent,
            sector=state.sector,
            reason=reason
        )
        
        return signal
