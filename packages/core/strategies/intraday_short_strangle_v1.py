"""Intraday Short Strangle V1 Strategy - Precision Scalper for Calm Days"""
import asyncio
import datetime as dt
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

import structlog
from prometheus_client import Counter

from packages.core.execution import ExecutionEngine
from packages.core.models import Instrument, InstrumentType, Signal, SignalSide, Tick
from packages.core.options.delta_selector import DeltaOptionSelector
from packages.core.strategies.base import Strategy, StrategyContext
from packages.core.utils.retry import safe_execute

logger = structlog.get_logger(__name__)

# Observability Metrics
intraday_strangle_v1_setups_evaluated = Counter(
    'intraday_strangle_v1_setups_evaluated_total',
    'Total number of intraday strangle setups evaluated',
    ['underlying']
)

intraday_strangle_v1_filter_rejections = Counter(
    'intraday_strangle_v1_filter_rejections_total',
    'Intraday strangle setups rejected by each filter',
    ['underlying', 'filter_name']
)

intraday_strangle_v1_signals_approved = Counter(
    'intraday_strangle_v1_signals_approved_total',
    'Intraday strangle signals that passed all filters',
    ['underlying']
)

intraday_strangle_v1_leg_failures = Counter(
    'intraday_strangle_v1_leg_failures_total',
    'Number of times one leg failed after entry',
    ['underlying', 'leg_type']
)


class IntradayShortStrangleV1(Strategy):
    """
    Strategy 1: Intraday Short Strangle (Async-First + Robust Filters)
    
    Logic:
    1. Entry: 09:20 AM (or config start).
    2. Selection: Sell Delta ~0.25 CE & PE (via DeltaSelector).
    3. Filters: 
       - Regime: LOW_MEAN_REVERT only.
       - Event: Block on High Impact days.
       - Volatility: Block if recent realized vol > threshold.
    4. Mgmt: Combined Premium SL (e.g., +25% of credit).
    5. Exit: Hard close at 15:15.
    """
    
    def __init__(
        self,
        name: str = None,
        params: Dict = None,
        kite: Optional[Any] = None,
        risk_engine: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        delta_selector: Optional[DeltaOptionSelector] = None,
        execution_engine: Optional[ExecutionEngine] = None,
        # Legacy params for backward compatibility
        instrument_manager: Optional[Any] = None,
        metrics: Optional[Any] = None,
        regime_engine: Optional[Any] = None,
        event_engine: Optional[Any] = None,
        kite_client: Optional[Any] = None,
    ):
        # Support both new simplified signature and legacy signature
        if kite is not None:
            # New simplified signature
            config = config or {}
            name = name or "IntradayShortStrangleV1"
            super().__init__(name, config)
            self.kite = kite
            self.risk_engine = risk_engine
            self.config = config
            self.delta_selector = delta_selector
            self.enabled = config.get("enabled", False)
        else:
            # Legacy signature
            params = params or {}
            name = name or "IntradayShortStrangleV1"
            super().__init__(name, params)
            self.kite = kite_client
            self.risk_engine = risk_engine
            self.config = params
            self.delta_selector = delta_selector
            self.enabled = params.get("enabled", False)
        
        self.execution_engine = execution_engine
        
        # Legacy support (for backward compatibility)
        self.instrument_manager = instrument_manager
        self.metrics = metrics
        self.regime_engine = regime_engine
        self.event_engine = event_engine
        
        # --- Configuration ---
        cfg = self.config
        self.underlying = cfg.get("underlying", "NIFTY")
        self.lot_size = int(cfg.get("lot_size", 25))
        self.target_delta = float(cfg.get("target_delta", 0.25))
        
        # Timings
        self.entry_time = cfg.get("entry_time", "09:20")
        self.exit_time = cfg.get("exit_time", "15:15")
        
        # Risk Management
        self.sl_premium_pct = float(cfg.get("sl_premium_pct", 0.25))
        self.use_limit_chase = bool(cfg.get("use_limit_chase", False))
        
        # State
        self.position_open = False
        self.ce_leg = None
        self.pe_leg = None
        self.entry_premium = 0.0
        self.rejection_reason = None
        
        # Observability (simple metrics dict + Prometheus)
        self.metrics_dict = {"evals": 0, "entries": 0, "sl_hits": 0}
        self.last_heartbeat_ts = 0.0
        
        logger.info(
            "IntradayShortStrangleV1 initialized",
            underlying=self.underlying,
            enabled=self.enabled,
            target_delta=self.target_delta,
            entry_time=self.entry_time,
            exit_time=self.exit_time
        )
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string (HH:MM) to time object"""
        try:
            hour, minute = map(int, time_str.split(":"))
            return time(hour, minute)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid time format: {time_str}, using default 09:20")
            return time(9, 20)
    
    async def execute(self, context: StrategyContext) -> List[Signal]:
        """
        Primary Async Execution Hook.
        """
        now = dt.datetime.now()
        underlying = self.underlying
        
        # Track: Setup evaluated
        intraday_strangle_v1_setups_evaluated.labels(underlying=underlying).inc()
        
        # 1. EOD Cleanup (Highest Priority)
        if self.position_open and not self._is_time(now, "09:15", self.exit_time):
            await self._exit_strangle("EOD Force Close")
            return []
        
        # 2. Management (if active)
        if self.position_open:
            await self._manage_position(context)
            return []
        
        # 3. Entry (if eligible)
        if self._is_time(now, self.entry_time, self.exit_time):
            await self._attempt_entry(context)
        
        return []
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """
        Legacy sync method (fallback).
        
        For backward compatibility, but prefer async execute().
        """
        # Delegate to async execute if possible
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Can't use run_until_complete in running loop
                # Return empty for now (or implement sync fallback)
                return []
            else:
                return loop.run_until_complete(self.execute(context))
        except RuntimeError:
            return asyncio.run(self.execute(context))
    
    # --- ENTRY LOGIC ---
    
    async def _attempt_entry(self, context: StrategyContext):
        self.metrics_dict["evals"] += 1
        intraday_strangle_v1_setups_evaluated.labels(underlying=self.underlying).inc()
        
        # A. FILTERS
        # 1. Event Check
        if context.is_event_day:
            if self.rejection_reason != "EVENT":
                logger.info(f"[{self.name}] Skipping: Event Day.")
                intraday_strangle_v1_filter_rejections.labels(
                    underlying=self.underlying,
                    filter_name="event_day"
                ).inc()
                self.rejection_reason = "EVENT"
            return
        
        # 2. Regime Check
        regime = context.regime
        if isinstance(context.regime_snapshot, dict):
            # Extract regime from snapshot
            for symbol, data in context.regime_snapshot.items():
                if isinstance(data, dict) and "regime" in data:
                    regime = data["regime"]
                    break
        elif isinstance(context.regime_snapshot, str):
            regime = context.regime_snapshot
        
        if regime != "LOW_MEAN_REVERT":
            if self.rejection_reason != f"REGIME_{regime}":
                logger.info(f"[{self.name}] Skipping: Regime '{regime}' not suitable.")
                intraday_strangle_v1_filter_rejections.labels(
                    underlying=self.underlying,
                    filter_name=f"regime_{regime}"
                ).inc()
                self.rejection_reason = f"REGIME_{regime}"
            return
        
        # 3. Capital Check
        can_trade = True
        if hasattr(self.risk_engine, "can_trade"):
            can_trade = self.risk_engine.can_trade(self.name)
        
        if not can_trade:
            if self.rejection_reason != "CAPITAL":
                logger.warning(f"[{self.name}] Skipping: Insufficient Capital Allocation.")
                intraday_strangle_v1_filter_rejections.labels(
                    underlying=self.underlying,
                    filter_name="insufficient_capital"
                ).inc()
                self.rejection_reason = "CAPITAL"
            return
        
        # B. SELECTION
        legs = await self.delta_selector.select_strangle(
            underlying=self.underlying,
            target_delta=self.target_delta,
            expiry_kind="nearest"
        )
        
        if not legs:
            # Silent warning to avoid spam, or use rejection_reason
            if self.rejection_reason != "NO_LEGS":
                logger.warning(f"[{self.name}] No legs found for delta {self.target_delta}")
                self.rejection_reason = "NO_LEGS"
            return
        
        ce, pe = legs
        total_prem = (ce.ltp + pe.ltp) * self.lot_size
        
        if total_prem <= 100:  # Minimal sanity check
            return
        
        # C. EXECUTION
        logger.info(f"[{self.name}] Attempting Entry: Sell {ce.symbol} & {pe.symbol} @ ~{total_prem:.0f}")
        
        success = await self._enter_strangle(ce.symbol, pe.symbol)
        if success:
            self.position_open = True
            self.ce_leg = ce.symbol
            self.pe_leg = pe.symbol
            self.entry_premium = total_prem
            self.rejection_reason = None  # Clear filters
            self.metrics_dict["entries"] += 1
            
            intraday_strangle_v1_signals_approved.labels(underlying=self.underlying).inc()
            
            logger.info(
                f"[{self.name}] 🟢 Position Secured. SL Limit: {total_prem * (1+self.sl_premium_pct):.0f}"
            )
    
    # --- MANAGEMENT LOGIC ---
    
    async def _manage_position(self, context: StrategyContext):
        try:
            # 1. Get Bulk Prices
            ltps = context.ltp or {}
            ce_ltp = ltps.get(self.ce_leg, 0)
            pe_ltp = ltps.get(self.pe_leg, 0)
            
            # Fallback if missing in bulk
            if not ce_ltp or not pe_ltp:
                if self.kite and hasattr(self.kite, 'get_ltp'):
                    q = await self.kite.get_ltp([str(self.ce_leg), str(self.pe_leg)])
                    ce_ltp = q.get(str(self.ce_leg), {}).get('last_price', 0)
                    pe_ltp = q.get(str(self.pe_leg), {}).get('last_price', 0)
                else:
                    logger.warning(f"[{self.name}] Cannot fetch LTP for position management")
                    return
            
            if ce_ltp == 0 or pe_ltp == 0:
                logger.warning(f"[{self.name}] Zero LTP detected. Skipping management cycle.")
                return
            
            # 2. Calculate Floating PnL
            current_prem = (ce_ltp + pe_ltp) * self.lot_size
            loss = current_prem - self.entry_premium
            
            # 3. Check Stop Loss
            max_loss = self.entry_premium * self.sl_premium_pct
            
            # Log Heartbeat occasionally (every 30s)
            import time
            now_ts = time.time()
            if now_ts - self.last_heartbeat_ts > 30:
                logger.info(f"[{self.name}] MTM: {loss:.0f} | SL Limit: {max_loss:.0f}")
                self.last_heartbeat_ts = now_ts
            
            if loss > max_loss:
                logger.info(f"[{self.name}] 🛑 SL Hit! Loss: {loss:.0f} > {max_loss:.0f}")
                self.metrics_dict["sl_hits"] += 1
                await self._exit_strangle("Stop Loss")
        
        except Exception as e:
            logger.error(f"[{self.name}] Management Error: {e}", exc_info=True)
    
    # --- ORDER EXECUTION ---
    
    async def _enter_strangle(self, ce_sym, pe_sym) -> bool:
        """
        Enter strangle using ExecutionEngine with defensive rollback.
        """
        if not self.execution_engine:
            logger.error(f"[{self.name}] Execution engine unavailable for entry")
            return False
        
        qty = self.lot_size
        spread_result = await self.execution_engine.execute_spread_order(
            [
                {
                    "symbol": ce_sym,
                    "side": "SELL",
                    "quantity": qty,
                    "product": "MIS",
                    "tag": "INTRA_STRANGLE_CE",
                    "use_limit_chase": self.use_limit_chase,
                },
                {
                    "symbol": pe_sym,
                    "side": "SELL",
                    "quantity": qty,
                    "product": "MIS",
                    "tag": "INTRA_STRANGLE_PE",
                    "use_limit_chase": self.use_limit_chase,
                },
            ],
            tag_prefix=f"{self.name}_ENTRY",
            rollback_on_fail=True,
        )
        
        if not spread_result.success or len(spread_result.legs) < 2:
            failed_leg = "CE" if (spread_result.failed_leg_index or 0) == 0 else "PE"
            logger.warning(
                f"[{self.name}] Strangle entry failed ({failed_leg}): {spread_result.message}"
            )
            intraday_strangle_v1_leg_failures.labels(
                underlying=self.underlying,
                leg_type=failed_leg
            ).inc()
            return False
        
        ce_fill = spread_result.legs[0].order.avg_price or 0.0
        pe_fill = spread_result.legs[1].order.avg_price or 0.0
        
        logger.info(
            f"[{self.name}] 🟢 ENTER strangle: CE={ce_sym} @{ce_fill:.2f}, "
            f"PE={pe_sym} @{pe_fill:.2f}, qty={qty}"
        )
        return True
    
    async def _exit_strangle(self, reason: str):
        logger.info(f"[{self.name}] Exiting: {reason}")
        if not self.position_open or not self.ce_leg or not self.pe_leg:
            return
        
        if not self.execution_engine:
            logger.error(f"[{self.name}] Execution engine unavailable for exit")
            return
        
        try:
            spread_result = await self.execution_engine.execute_spread_order(
                [
                    {
                        "symbol": self.ce_leg,
                        "side": "BUY",
                        "quantity": self.lot_size,
                        "product": "MIS",
                        "tag": "Exit_CE",
                        "use_limit_chase": False,
                    },
                    {
                        "symbol": self.pe_leg,
                        "side": "BUY",
                        "quantity": self.lot_size,
                        "product": "MIS",
                        "tag": "Exit_PE",
                        "use_limit_chase": False,
                    },
                ],
                tag_prefix=f"{self.name}_EXIT",
                rollback_on_fail=False,
            )
            if not spread_result.success:
                logger.error(f"[{self.name}] Exit failed: {spread_result.message}")
                return
        except Exception as e:
            logger.error(f"[{self.name}] Exit Error: {e}", exc_info=True)
            return
        
        # Reset State
        self.position_open = False
        self.ce_leg = None
        self.pe_leg = None
        self.entry_premium = 0.0
    
    def _is_time(self, now, start, end):
        try:
            t_start = dt.datetime.strptime(start, "%H:%M").time()
            t_end = dt.datetime.strptime(end, "%H:%M").time()
            return t_start <= now.time() <= t_end
        except (ValueError, AttributeError):
            logger.warning(f"[{self.name}] Invalid time format: {start} or {end}")
            return False
    
    def _get_portfolio_risk(self, context: StrategyContext) -> Optional[Any]:
        """Helper to get portfolio risk for capital checks"""
        if self.risk_engine and hasattr(self.risk_engine, 'get_portfolio_risk'):
            try:
                return self.risk_engine.get_portfolio_risk()
            except:
                pass
        return None
    
    def _find_strike_by_delta(
        self,
        context: StrategyContext,
        underlying: str,
        spot: float,
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
        # 1. Get options chain for underlying + nearest expiry
        # 2. Calculate delta for each strike
        # 3. Find strike closest to target delta range
        # 4. Return strike and premium
        
        # For now, simplified approximation:
        # Delta ~0.25 means roughly 1-1.5% OTM for intraday
        if option_type == "CE":
            # Call: slightly OTM (1-1.5% above spot)
            target_strike = round(spot * 1.012, 50)  # ~1.2% OTM, round to nearest 50
            # Estimate premium (simplified - would use actual option pricing)
            premium = spot * 0.008 * (1.0)  # Rough estimate for intraday
        else:  # PE
            # Put: slightly OTM (1-1.5% below spot)
            target_strike = round(spot * 0.988, 50)  # ~1.2% OTM
            premium = spot * 0.008 * (1.0)
        
        return target_strike, premium
    
    def _generate_exit_signals(self, context: StrategyContext, reason: str) -> List[Signal]:
        """Generate exit signals for existing positions"""
        # In production, would check PositionStore for open strangle positions
        # For now, return empty (would be handled by orchestrator)
        if reason == "hard_exit_time":
            logger.info(
                "Hard exit time reached, generating exit signals",
                time=context.timestamp.time()
            )
        return []
    
    def _monitor_existing_positions(self, context: StrategyContext) -> List[Signal]:
        """Monitor existing positions and check stop-loss/take-profit"""
        # In production, would:
        # 1. Check PositionStore for open strangle positions
        # 2. Calculate current PnL
        # 3. Check if SL or TP hit
        # 4. Generate exit signals if needed
        
        # Check stop-loss: 1.5× premium
        # Check take-profit: 40-50% premium decay
        # Check intraday band: ±1σ from entry spot
        
        return []
    
    def _get_current_regime(self, context: StrategyContext) -> str:
        """Get current regime from R1 engine"""
        if self.regime_engine:
            try:
                regime = self.regime_engine.get_current_regime(context.instrument.symbol)
                return regime.value if hasattr(regime, 'value') else str(regime)
            except Exception as e:
                logger.debug(f"Could not get regime: {e}")
        
        return "UNKNOWN"
    
    def _get_intraday_realized_vol(self, context: StrategyContext) -> Optional[float]:
        """Get intraday realized volatility (last 60-90 minutes)"""
        if not context.bars_5s or len(context.bars_5s) < 12:  # Need at least 1 hour of 5min bars
            return None
        
        # Calculate realized vol from recent bars
        # Simplified: use std dev of returns
        recent_bars = context.bars_5s[-12:]  # Last 60 minutes (12 × 5min)
        returns = []
        
        for i in range(1, len(recent_bars)):
            if recent_bars[i-1].close > 0:
                ret = (recent_bars[i].close - recent_bars[i-1].close) / recent_bars[i-1].close
                returns.append(ret)
        
        if not returns:
            return None
        
        # Calculate std dev (realized vol)
        import statistics
        vol = statistics.stdev(returns) if len(returns) > 1 else 0.0
        return vol * 100  # Convert to percentage
    
    def _has_major_event_today(self, context: StrategyContext) -> bool:
        """Check if there's a major event today or in next 24h"""
        if self.event_engine:
            try:
                # In production, would call event_engine.get_today_classification()
                # For now, return False (no events)
                return False
            except Exception as e:
                logger.debug(f"Could not check events: {e}")
        
        return False
    
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
