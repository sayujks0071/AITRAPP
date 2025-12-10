"""Trend Credit Spread V1 Strategy - Regime and Trend-Aware Vertical Spreads"""
import asyncio
import datetime as dt
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Literal

import structlog
from prometheus_client import Counter

from packages.core.execution import ExecutionEngine
from packages.core.models import Instrument, Signal, SignalSide
from packages.core.strategies.base import Strategy, StrategyContext
from packages.core.options.delta_selector import DeltaOptionSelector, OptionCandidate

logger = structlog.get_logger(__name__)

# Observability Metrics
trend_credit_spread_v1_setups_evaluated = Counter(
    'trend_credit_spread_v1_setups_evaluated_total',
    'Total number of trend credit spread setups evaluated',
    ['underlying', 'direction']
)

trend_credit_spread_v1_filter_rejections = Counter(
    'trend_credit_spread_v1_filter_rejections_total',
    'Trend credit spread setups rejected by each filter',
    ['underlying', 'direction', 'filter_name']
)

trend_credit_spread_v1_signals_approved = Counter(
    'trend_credit_spread_v1_signals_approved_total',
    'Trend credit spread signals that passed all filters',
    ['underlying', 'direction']
)

Direction = Literal["BULL_PUT", "BEAR_CALL"]


class TrendCreditSpreadV1(Strategy):
    """
    Regime- and trend-aware credit spread strategy:
    
    - Uses EMA + ADX trend filter
    - Uses shared DeltaOptionSelector for short/long leg selection
    - One position at a time
    - Async-first: execute(context) is the primary entry point
    """
    
    def __init__(
        self,
        name: str,
        params: Dict,
        instrument_manager: Optional[Any] = None,
        risk_engine: Optional[Any] = None,
        metrics: Optional[Any] = None,
        kite_client: Optional[Any] = None,
        position_store: Optional[Any] = None,
        delta_selector: Optional[DeltaOptionSelector] = None,
        regime_engine: Optional[Any] = None,
        event_engine: Optional[Any] = None,
        execution_engine: Optional[ExecutionEngine] = None,
    ):
        super().__init__(name, params)
        
        self.kite = kite_client
        self.risk_engine = risk_engine
        self.config = params
        self.delta_selector = delta_selector
        self.position_store = position_store
        self.enabled = params.get("enabled", False)
        self.execution_engine = execution_engine
        
        # Legacy support
        self.instrument_manager = instrument_manager
        self.metrics = metrics
        self.regime_engine = regime_engine
        self.event_engine = event_engine
        
        # Configuration
        self.underlying = params.get("underlying", "NIFTY")
        self.direction: Direction = params.get("direction", "BULL_PUT")
        
        # Lot sizing
        self.lot_size = int(params.get("lot_size", 25))
        self.max_positions = int(params.get("max_positions", 1))
        
        # Timing
        self.entry_time = params.get("entry_time", "10:00")
        # Support both naming conventions
        self.last_entry_time = params.get("last_entry_time", params.get("exit_time", "14:00"))
        self.hard_exit_time = params.get("hard_exit_time", params.get("exit_time", "15:10"))
        
        # Option selection
        self.expiry_kind = params.get("expiry_kind", "nearest")
        self.target_delta_short = float(params.get("target_delta_short", 0.25))
        # Support both naming conventions
        self.width_points = float(params.get("wing_width_pts", params.get("width_points", 100.0)))
        
        # Trend filter
        self.timeframe = params.get("timeframe", "5minute")
        self.ema_fast = int(params.get("ema_fast", 21))
        self.ema_slow = int(params.get("ema_slow", 55))
        self.adx_period = int(params.get("adx_period", 14))
        self.adx_threshold = float(params.get("adx_threshold", 22.0))
        
        # Risk filters
        self.min_iv_rank = float(params.get("min_iv_rank", 0.25))
        self.max_iv_rank = float(params.get("max_iv_rank", 0.85))
        # Support both naming conventions
        self.max_portfolio_heat_pct = float(params.get("max_portfolio_heat", params.get("max_portfolio_heat_pct", 0.02)))
        self.max_margin_pct = float(params.get("max_margin_util", params.get("max_margin_pct", 0.30)))
        # Support both naming conventions
        self.daily_loss_cap = float(params.get("max_loss_rs", params.get("daily_loss_cap", 5000)))
        self.min_credit = float(params.get("min_credit", 1000.0))
        self.target_profit_pct = float(params.get("target_profit_pct", 0.5))
        
        # Execution toggles
        self.use_limit_chase = bool(params.get("use_limit_chase", False))
        
        # Book-keeping
        self.current_position_id: Optional[str] = None
        self.short_leg_symbol: Optional[str] = None
        self.long_leg_symbol: Optional[str] = None
        self.entry_credit: float = 0.0
        self.entry_timestamp: Optional[datetime] = None
        
        logger.info(
            "TrendCreditSpreadV1 initialized",
            underlying=self.underlying,
            direction=self.direction,
            enabled=self.enabled,
            target_delta_short=self.target_delta_short,
            width_points=self.width_points
        )
    
    # ---------- PUBLIC ENTRYPOINT ----------
    
    async def execute(self, context: StrategyContext) -> List[Signal]:
        """
        Primary Async Execution Hook.
        """
        if not self.enabled:
            return []
        
        now = dt.datetime.now()
        underlying = self.underlying
        
        # Track: Setup evaluated
        trend_credit_spread_v1_setups_evaluated.labels(
            underlying=underlying,
            direction=self.direction
        ).inc()
        
        # 1) Time gates
        if not self._within_trading_window(now):
            if self._must_flatten(now) and self._has_open_position():
                await self._exit_spread(reason="hard_exit_time")
            return []
        
        # 2) Strategy-level risk + global risk
        if not self._risk_ok(context):
            return []
        
        # 3) If we already have a spread, manage it
        if self._has_open_position():
            await self._manage_spread(context)
            return []
        
        # 4) Flat → see if we can open a new spread
        await self._attempt_entry(context)
        
        return []
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """
        Legacy sync method (fallback).
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return []
            else:
                return loop.run_until_complete(self.execute(context))
        except RuntimeError:
            return asyncio.run(self.execute(context))
    
    # ---------- CORE LOGIC ----------
    
    async def _attempt_entry(self, context: StrategyContext) -> None:
        # Regime & event filters
        if not self._regime_ok(context):
            self._inc_filter("regime")
            return
        
        if not self._event_ok(context):
            self._inc_filter("event")
            return
        
        # Trend filter
        trend_ok = await self._trend_confirmed(context)
        if not trend_ok:
            self._inc_filter("trend")
            return
        
        # IV / heat / margin filters
        if not self._iv_ok(context):
            self._inc_filter("iv_rank")
            return
        
        if not self._portfolio_heat_ok(context):
            self._inc_filter("portfolio_heat")
            return
        
        if not self._margin_ok(context):
            self._inc_filter("margin")
            return
        
        # Delta legs (async method)
        if not self.delta_selector:
            logger.warning(f"[{self.name}] DeltaOptionSelector not available")
            return
        
        legs = await self.delta_selector.select_credit_spread(
            underlying=self.underlying,
            direction=self.direction,
            target_delta_short=self.target_delta_short,
            width_points=self.width_points,
            expiry_kind=self.expiry_kind,
        )
        
        if not legs:
            self._inc_filter("delta_selection")
            return
        
        short_leg, long_leg = legs
        
        # Final risk check: capital per spread
        if not self._position_sizing_ok(short_leg, long_leg, context):
            self._inc_filter("position_size")
            return
        
        await self._enter_spread(short_leg, long_leg)
    
    async def _manage_spread(self, context: StrategyContext) -> None:
        """
        Very simple management skeleton:
        - Exit if PnL hits target or SL
        - Exit on hard exit time
        """
        if not self.current_position_id and not (self.short_leg_symbol and self.long_leg_symbol):
            return
        
        # Get current prices from context.ltp
        ltps = context.ltp or {}
        short_ltp = ltps.get(self.short_leg_symbol, 0) if self.short_leg_symbol else 0
        long_ltp = ltps.get(self.long_leg_symbol, 0) if self.long_leg_symbol else 0
        
        # Fallback fetch if missing
        if not short_ltp or not long_ltp:
            if self.kite and hasattr(self.kite, 'ltp'):
                try:
                    instrument_keys = [
                        f"NFO:{self.short_leg_symbol}",
                        f"NFO:{self.long_leg_symbol}"
                    ]
                    q = self.kite.ltp(instrument_keys)
                    if isinstance(q, dict):
                        short_data = q.get(f"NFO:{self.short_leg_symbol}", {})
                        long_data = q.get(f"NFO:{self.long_leg_symbol}", {})
                        short_ltp = short_data.get("last_price", 0) if isinstance(short_data, dict) else 0
                        long_ltp = long_data.get("last_price", 0) if isinstance(long_data, dict) else 0
                except Exception as e:
                    logger.debug(f"[{self.name}] LTP fetch failed: {e}")
        
        if short_ltp == 0 or long_ltp == 0:
            return
        
        # Calculate current credit (for credit spreads: short premium - long premium)
        current_credit = (short_ltp - long_ltp) * self.lot_size
        
        # PnL = entry_credit - current_credit (positive when credit shrinks = profit)
        pnl = self.entry_credit - current_credit
        
        # Stop loss: use max_loss_rs (absolute) or percentage of credit
        max_loss = self.daily_loss_cap  # Use max_loss_rs as absolute stop loss
        if pnl <= -max_loss:
            logger.info(f"[{self.name}] 🛑 SL Hit! PnL: {pnl:.0f} <= -{max_loss:.0f}")
            await self._exit_spread(reason="stop_loss")
            return
        
        # Take profit: use target_profit_pct of credit collected
        target_profit = self.entry_credit * self.target_profit_pct
        if pnl >= target_profit:
            logger.info(f"[{self.name}] ✅ TP Hit! PnL: {pnl:.0f} >= {target_profit:.0f}")
            await self._exit_spread(reason="take_profit")
            return
    
    async def _enter_spread(
        self,
        short_leg: OptionCandidate,
        long_leg: OptionCandidate,
    ) -> None:
        if not self.execution_engine:
            logger.error(f"[{self.name}] Execution engine unavailable for spread entry")
            return
        
        qty = self.lot_size
        spread_result = await self.execution_engine.execute_spread_order(
            [
                {
                    "symbol": short_leg.symbol,
                    "side": "SELL",
                    "quantity": qty,
                    "product": "NRML",
                    "tag": f"{self.name}_SHORT",
                    "use_limit_chase": self.use_limit_chase,
                },
                {
                    "symbol": long_leg.symbol,
                    "side": "BUY",
                    "quantity": qty,
                    "product": "NRML",
                    "tag": f"{self.name}_LONG",
                    "use_limit_chase": self.use_limit_chase,
                },
            ],
            tag_prefix=f"{self.name}_ENTRY",
            rollback_on_fail=True,
        )
        
        if not spread_result.success or len(spread_result.legs) < 2:
            logger.warning(
                f"[{self.name}] Spread entry failed: {spread_result.message}"
            )
            return
        
        short_price = spread_result.legs[0].order.avg_price or short_leg.ltp
        long_price = spread_result.legs[1].order.avg_price or long_leg.ltp
        entry_credit = (short_price - long_price) * qty
        
        if entry_credit <= 0:
            logger.warning(f"[{self.name}] Invalid credit after execution: {entry_credit}")
            return
        
        self.current_position_id = f"{self.name}_{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.short_leg_symbol = short_leg.symbol
        self.long_leg_symbol = long_leg.symbol
        self.entry_credit = entry_credit
        self.entry_timestamp = dt.datetime.now()
        
        trend_credit_spread_v1_signals_approved.labels(
            underlying=self.underlying,
            direction=self.direction
        ).inc()
        
        logger.info(
            f"[{self.name}] 🟢 Spread Entered. Credit: {entry_credit:.0f}"
        )
    
    async def _exit_spread(self, reason: str) -> None:
        if not self.short_leg_symbol or not self.long_leg_symbol:
            return
        
        logger.info(f"[{self.name}] Exiting spread ({reason})")
        
        if not self.execution_engine:
            logger.error(f"[{self.name}] Execution engine unavailable for exit")
            return
        
        spread_result = await self.execution_engine.execute_spread_order(
            [
                {
                    "symbol": self.short_leg_symbol,
                    "side": "BUY",
                    "quantity": self.lot_size,
                    "product": "NRML",
                    "tag": "Exit_Short",
                    "use_limit_chase": False,
                },
                {
                    "symbol": self.long_leg_symbol,
                    "side": "SELL",
                    "quantity": self.lot_size,
                    "product": "NRML",
                    "tag": "Exit_Long",
                    "use_limit_chase": False,
                },
            ],
            tag_prefix=f"{self.name}_EXIT",
            rollback_on_fail=False,
        )
        
        if not spread_result.success:
            logger.error(
                f"[{self.name}] Error exiting spread: {spread_result.message}"
            )
            return
        
        self.current_position_id = None
        self.short_leg_symbol = None
        self.long_leg_symbol = None
        self.entry_credit = 0.0
        self.entry_timestamp = None

    
    # ---------- FILTERS & HELPERS ----------
    
    def _within_trading_window(self, now: dt.datetime) -> bool:
        t = now.time()
        entry_start = dt.datetime.strptime(self.entry_time, "%H:%M").time()
        last_entry = dt.datetime.strptime(self.last_entry_time, "%H:%M").time()
        return entry_start <= t <= last_entry
    
    def _must_flatten(self, now: dt.datetime) -> bool:
        t = now.time()
        hard_exit = dt.datetime.strptime(self.hard_exit_time, "%H:%M").time()
        return t >= hard_exit
    
    def _has_open_position(self) -> bool:
        return bool(self.current_position_id and self.short_leg_symbol and self.long_leg_symbol)
    
    def _risk_ok(self, context: StrategyContext) -> bool:
        # Strategy-level daily loss
        if self.risk_engine and hasattr(self.risk_engine, 'get_strategy_pnl'):
            try:
                strat_pnl = self.risk_engine.get_strategy_pnl(self.name)
                if strat_pnl <= -self.daily_loss_cap:
                    self._inc_filter("daily_loss_cap")
                    return False
            except:
                pass
        
        # Global loss check (simplified - check context margins)
        if context.available_margin <= 0:
            self._inc_filter("no_margin")
            return False
        
        return True
    
    def _regime_ok(self, context: StrategyContext) -> bool:
        if not context.regime_snapshot:
            return True
        
        # Extract regime from snapshot
        regime = context.regime
        if isinstance(context.regime_snapshot, dict):
            for symbol, data in context.regime_snapshot.items():
                if isinstance(data, dict) and "regime" in data:
                    regime = data["regime"]
                    break
        
        if regime in ("HIGH_EVENT", "CHAOTIC"):
            return False
        return True
    
    def _event_ok(self, context: StrategyContext) -> bool:
        if context.is_event_day:
            # Check event impact level
            if hasattr(context, 'event_impact') and context.event_impact == "HIGH":
                return False
        return True
    
    async def _trend_confirmed(self, context: StrategyContext) -> bool:
        """
        EMA + ADX check on underlying index.
        Uses context.bars_5s if available, otherwise falls back to fetching.
        """
        try:
            # Try to use bars from context first
            bars = context.bars_5s if hasattr(context, 'bars_5s') and context.bars_5s else []
            
            if not bars or len(bars) < max(self.ema_slow + 5, self.adx_period + 10):
                # Not enough data in context, skip trend check for now
                # In production, would fetch from market data stream
                logger.debug(f"[{self.name}] Insufficient bars for trend check: {len(bars)}")
                return False
            
            # Convert bars to DataFrame
            import pandas as pd
            df_data = {
                'timestamp': [b.timestamp for b in bars],
                'open': [b.open for b in bars],
                'high': [b.high for b in bars],
                'low': [b.low for b in bars],
                'close': [b.close for b in bars],
                'volume': [b.volume for b in bars],
            }
            df = pd.DataFrame(df_data)
            
            close = df["close"]
            high = df["high"]
            low = df["low"]
            
            # Calculate EMAs
            ema_fast = close.ewm(span=self.ema_fast, adjust=False).mean()
            ema_slow = close.ewm(span=self.ema_slow, adjust=False).mean()
            
            # Calculate ADX (simplified)
            try:
                # Try to use pandas_ta if available
                import pandas_ta as ta
                adx_result = ta.adx(high, low, close, length=self.adx_period)
                if isinstance(adx_result, pd.DataFrame):
                    adx_col = f'ADX_{self.adx_period}'
                    if adx_col in adx_result.columns:
                        adx_series = adx_result[adx_col]
                    else:
                        # Try alternative column names
                        adx_series = adx_result.iloc[:, 0] if len(adx_result.columns) > 0 else pd.Series([0.0] * len(df))
                else:
                    adx_series = pd.Series([0.0] * len(df))
            except (ImportError, AttributeError, KeyError, IndexError):
                # Fallback: simple ADX calculation
                adx_series = self._calculate_simple_adx(high, low, close, self.adx_period)
            
            current_fast = ema_fast.iloc[-1]
            current_slow = ema_slow.iloc[-1]
            current_adx = float(adx_series.iloc[-1]) if not adx_series.empty else 0.0
            
            if self.direction == "BULL_PUT":
                trending = current_fast > current_slow and current_adx >= self.adx_threshold
            else:  # BEAR_CALL
                trending = current_fast < current_slow and current_adx >= self.adx_threshold
            
            return trending
        
        except Exception as e:
            logger.error(f"[{self.name}] Trend check failed: {e}", exc_info=True)
            return False
    
    def _calculate_simple_adx(self, high, low, close, period: int):
        """Simplified ADX calculation"""
        import pandas as pd
        import numpy as np
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate Directional Movement
        up_move = high - high.shift()
        down_move = low.shift() - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Smooth TR and DM
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (pd.Series(plus_dm).rolling(window=period).mean() / atr)
        minus_di = 100 * (pd.Series(minus_dm).rolling(window=period).mean() / atr)
        
        # Calculate DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx.fillna(0)
    
    def _iv_ok(self, context: StrategyContext) -> bool:
        # Placeholder: IV rank check
        # In production, would fetch from vol engine
        if self.regime_engine and hasattr(self.regime_engine, 'get_iv_percentile'):
            try:
                iv_pct = self.regime_engine.get_iv_percentile(self.underlying)
                if iv_pct:
                    iv_rank = iv_pct / 100.0
                    return self.min_iv_rank <= iv_rank <= self.max_iv_rank
            except:
                pass
        # Default: allow if no IV data available
        return True
    
    def _portfolio_heat_ok(self, context: StrategyContext) -> bool:
        if self.risk_engine and hasattr(self.risk_engine, 'get_portfolio_heat_pct'):
            try:
                heat = self.risk_engine.get_portfolio_heat_pct()
                return heat <= self.max_portfolio_heat_pct
            except:
                pass
        # Fallback: check context margins
        if context.net_liquid > 0:
            used_margin = context.net_liquid - context.available_margin
            heat_pct = (used_margin / context.net_liquid) * 100
            return heat_pct <= (self.max_portfolio_heat_pct * 100)
        return True
    
    def _margin_ok(self, context: StrategyContext) -> bool:
        if context.net_liquid > 0:
            used_margin = context.net_liquid - context.available_margin
            margin_pct = (used_margin / context.net_liquid) * 100
            return margin_pct <= (self.max_margin_pct * 100)
        return True
    
    def _position_sizing_ok(
        self,
        short_leg: OptionCandidate,
        long_leg: OptionCandidate,
        context: StrategyContext
    ) -> bool:
        # Rough margin estimate: width * lot_size * multiplier
        # For credit spreads, margin is typically the width of the spread
        est_margin = self.width_points * self.lot_size * 50  # Rough estimate (50 is NIFTY multiplier)
        
        # Check if we have enough available margin
        if context.available_margin < est_margin:
            return False
        
        # Check strategy capital allocation
        if self.risk_engine and hasattr(self.risk_engine, 'check_strategy_cap'):
            try:
                return self.risk_engine.check_strategy_cap(self.name, est_margin)
            except:
                pass
        
        return True
    
    # ---------- METRICS HELPERS ----------
    
    def _inc_filter(self, name: str) -> None:
        trend_credit_spread_v1_filter_rejections.labels(
            underlying=self.underlying,
            direction=self.direction,
            filter_name=name
        ).inc()
    
    def _inc_signal(self, name: str) -> None:
        # Can add more signal metrics if needed
        pass
