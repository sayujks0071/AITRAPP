"""Regime-Switching Volatility Engine (R1) - Meta-strategy that routes to A-G strategies based on volatility regimes"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Any, Dict, List, Optional

import structlog

from packages.core.models import Signal
from packages.core.strategies.base import Strategy, StrategyContext

logger = structlog.get_logger(__name__)


class VolRegime(IntEnum):
    """Volatility regime classification (numeric for metrics)"""
    UNKNOWN = 0
    LOW_MEAN_REVERT = 1
    MEDIUM_TREND = 2
    HIGH_EVENT = 3
    CHAOTIC = 4


@dataclass
class RegimeFeatures:
    """Computed features for regime classification"""
    iv_rank: float
    iv_percentile: float
    rv_iv_ratio: float
    atr_pct: float
    trend_strength: float
    vix_rank: float
    vix_slope: float


class MarketContextAdapter:
    """
    Adapter to convert StrategyContext to the interface expected by RegimeClassifier.
    This bridges your existing StrategyContext to the R1 engine's expectations.
    """
    
    def __init__(self, context: StrategyContext, instrument_manager=None, market_data_stream=None):
        self.context = context
        self.instrument = context.instrument
        self.underlying = context.instrument.symbol
        self.spot = context.latest_tick.last_price if context.latest_tick else 0.0
        self.instrument_manager = instrument_manager
        self.market_data_stream = market_data_stream
        
        # Cache for computed values
        self._iv_rank_cache: Dict[int, float] = {}
        self._iv_percentile_cache: Dict[int, float] = {}
        self._realised_vol_cache: Dict[int, float] = {}
        self._implied_vol_cache: Optional[float] = None
        self._atr_cache: Dict[int, Optional[float]] = {}
        self._trend_strength_cache: Optional[float] = None
        self._vix_rank_cache: Dict[int, float] = {}
        self._vix_slope_cache: Optional[float] = None
    
    def iv_rank(self, days: int = 60) -> float:
        """Compute IV rank over N days"""
        if days in self._iv_rank_cache:
            return self._iv_rank_cache[days]
        
        # Use IV percentile from context if available, convert to rank (0-1)
        if self.context.iv_percentile is not None:
            rank = self.context.iv_percentile / 100.0
            self._iv_rank_cache[days] = rank
            return rank
        
        # Fallback: estimate from bars (simplified)
        if self.context.bars_5s and len(self.context.bars_5s) >= 20:
            # Use ATR as proxy for volatility
            closes = [b.close for b in self.context.bars_5s[-20:]]
            if len(closes) >= 20:
                returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
                vol = (sum(r**2 for r in returns) / len(returns)) ** 0.5 * (252 ** 0.5)  # Annualized
                # Normalize to 0-1 (rough estimate)
                rank = min(1.0, max(0.0, vol * 10))
                self._iv_rank_cache[days] = rank
                return rank
        
        return 0.5  # Default middle
    
    def iv_percentile(self, days: int = 60) -> float:
        """Compute IV percentile over N days"""
        if days in self._iv_percentile_cache:
            return self._iv_percentile_cache[days]
        
        if self.context.iv_percentile is not None:
            self._iv_percentile_cache[days] = self.context.iv_percentile
            return self.context.iv_percentile
        
        # Fallback: convert from rank
        rank = self.iv_rank(days)
        percentile = rank * 100.0
        self._iv_percentile_cache[days] = percentile
        return percentile
    
    def realised_vol(self, days: int = 10) -> float:
        """Compute realized volatility over N days"""
        if days in self._realised_vol_cache:
            return self._realised_vol_cache[days]
        
        if self.context.bars_5s and len(self.context.bars_5s) >= days:
            closes = [b.close for b in self.context.bars_5s[-days:]]
            if len(closes) >= 2:
                returns = []
                for i in range(1, len(closes)):
                    prev = closes[i - 1]
                    if prev == 0:
                        # Skip bad ticks to avoid divide-by-zero
                        continue
                    returns.append((closes[i] - prev) / prev)
                if returns:
                    vol = (sum(r**2 for r in returns) / len(returns)) ** 0.5
                    # Annualize (assuming 252 trading days, ~252*78 5-min bars per day)
                    annualized_vol = vol * (252 * 78) ** 0.5
                    self._realised_vol_cache[days] = annualized_vol
                    return annualized_vol
        
        return 0.20  # Default 20% annualized
    
    def implied_vol(self) -> float:
        """Get current implied volatility"""
        if self._implied_vol_cache is not None:
            return self._implied_vol_cache
        
        # Use IV from context if available
        if self.context.iv_percentile is not None:
            # Estimate IV from percentile (rough approximation)
            # In production, fetch from options chain
            iv = 0.15 + (self.context.iv_percentile / 100.0) * 0.20  # 15-35% range
            self._implied_vol_cache = iv
            return iv
        
        return 0.25  # Default 25%
    
    def atr(self, period: int = 14) -> Optional[float]:
        """Compute ATR over period"""
        if period in self._atr_cache:
            return self._atr_cache[period]
        
        if self.context.bars_5s and len(self.context.bars_5s) >= period:
            highs = [b.high for b in self.context.bars_5s[-period:]]
            lows = [b.low for b in self.context.bars_5s[-period:]]
            closes = [b.close for b in self.context.bars_5s[-period:]]
            
            if len(highs) == period:
                tr_values = []
                for i in range(1, len(highs)):
                    tr1 = highs[i] - lows[i]
                    tr2 = abs(highs[i] - closes[i-1])
                    tr3 = abs(lows[i] - closes[i-1])
                    tr_values.append(max(tr1, tr2, tr3))
                
                if tr_values:
                    atr = sum(tr_values) / len(tr_values)
                    self._atr_cache[period] = atr
                    return atr
        
        self._atr_cache[period] = None
        return None
    
    def trend_strength(self) -> float:
        """Compute trend strength (0-1 scale)"""
        if self._trend_strength_cache is not None:
            return self._trend_strength_cache
        
        if self.context.bars_5s and len(self.context.bars_5s) >= 20:
            closes = [b.close for b in self.context.bars_5s[-20:]]
            if len(closes) >= 20:
                # Simple EMA-based trend
                ema_fast = sum(closes[-9:]) / 9
                ema_slow = sum(closes[-20:]) / 20
                if ema_slow > 0:
                    trend_ratio = abs(ema_fast - ema_slow) / ema_slow
                    strength = min(1.0, trend_ratio * 10)  # Normalize to 0-1
                    self._trend_strength_cache = strength
                    return strength
        
        self._trend_strength_cache = 0.5
        return 0.5
    
    def vix_rank(self, days: int = 90) -> float:
        """Compute VIX rank over N days (placeholder - would fetch VIX data)"""
        if days in self._vix_rank_cache:
            return self._vix_rank_cache[days]
        
        # Placeholder: use IV rank as proxy
        rank = self.iv_rank(days)
        self._vix_rank_cache[days] = rank
        return rank
    
    def vix_slope(self) -> float:
        """Compute VIX slope (dVIX/dt)"""
        if self._vix_slope_cache is not None:
            return self._vix_slope_cache
        
        # Placeholder: estimate from IV changes
        if self.context.bars_5s and len(self.context.bars_5s) >= 10:
            # Use recent volatility changes as proxy
            recent_vol = self.realised_vol(days=5)
            older_vol = self.realised_vol(days=10)
            if older_vol > 0:
                slope = (recent_vol - older_vol) / older_vol
                self._vix_slope_cache = slope
                return slope
        
        self._vix_slope_cache = 0.0
        return 0.0


class RegimeClassifier:
    """
    Stateless classifier: takes pre-computed features and returns a regime.
    
    Uses shared thresholds for coarse bands, and optional per-regime
    conditions from config (regime_vol_engine.regimes.*.conditions) so the
    behaviour can be tuned from YAML instead of hard-coded guesses.
    """
    
    def __init__(self, shared_cfg: Dict[str, Any], regimes_cfg: Optional[Dict[str, Any]] = None):
        self.lookbacks = shared_cfg.get("lookbacks", {})
        self.th = shared_cfg.get("thresholds", {})
        # Optional fine-grained per-regime conditions
        self.regime_conditions = {
            name: cfg.get("conditions", {}) for name, cfg in (regimes_cfg or {}).items()
        }
    
    def compute_features(self, ctx: MarketContextAdapter) -> RegimeFeatures:
        """Compute feature vector from market context"""
        def safe_div(n: float, d: float, default: float = 0.0) -> float:
            return default if d is None or d == 0 else n / d

        try:
            iv_rank = ctx.iv_rank(days=self.lookbacks.get("iv_rank_days", 60))
            iv_pct = ctx.iv_percentile(days=self.lookbacks.get("iv_rank_days", 60))
            
            iv = max(ctx.implied_vol() or 0.0, 1e-6)  # Avoid divide-by-zero
            rv = ctx.realised_vol(days=self.lookbacks.get("rv_days", 10)) or 0.0
            rv_iv_ratio = safe_div(rv, iv, default=0.0)
            
            atr = ctx.atr(self.lookbacks.get("atr_period", 14))
            atr_pct = safe_div(atr or 0.0, ctx.spot or 0.0, default=0.0) * 100.0 if atr else 0.0
            
            trend_strength = ctx.trend_strength()
            vix_rank = ctx.vix_rank(days=self.lookbacks.get("vix_rank_days", 90))
            vix_slope = ctx.vix_slope()
        except ZeroDivisionError as e:
            logger.warning(
                "RegimeVolEngine compute_features caught divide-by-zero; returning safe defaults",
                error=str(e)
            )
            return RegimeFeatures(
                iv_rank=0.0,
                iv_percentile=0.0,
                rv_iv_ratio=0.0,
                atr_pct=0.0,
                trend_strength=0.0,
                vix_rank=0.0,
                vix_slope=0.0,
            )
        
        return RegimeFeatures(
            iv_rank=iv_rank,
            iv_percentile=iv_pct,
            rv_iv_ratio=rv_iv_ratio,
            atr_pct=atr_pct,
            trend_strength=trend_strength,
            vix_rank=vix_rank,
            vix_slope=vix_slope,
        )
    
    def classify(self, f: RegimeFeatures) -> VolRegime:
        """Classify regime based on computed features"""
        th = self.th
        
        # Helper to evaluate per-regime conditions from config
        def matches_conditions(name: str) -> bool:
            conds = self.regime_conditions.get(name, {})
            if not conds:
                return False
            
            def between(val: float, min_key: str, max_key: str) -> bool:
                lo = conds.get(min_key)
                hi = conds.get(max_key)
                if lo is not None and val < lo:
                    return False
                if hi is not None and val > hi:
                    return False
                return True
            
            # IV rank bounds
            if not between(f.iv_rank, "iv_rank_min", "iv_rank_max"):
                return False
            # ATR% bounds
            if not between(f.atr_pct, "atr_pct_min", "atr_pct_max"):
                return False
            # RV/IV ratio bounds
            if not between(f.rv_iv_ratio, "rv_iv_min", "rv_iv_max"):
                return False
            # Trend strength
            ts_min = conds.get("trend_strength_min")
            if ts_min is not None and f.trend_strength < ts_min:
                return False
            # VIX rank / slope
            vix_min = conds.get("vix_rank_min")
            if vix_min is not None and f.vix_rank < vix_min:
                return False
            vix_max = conds.get("vix_rank_max")
            if vix_max is not None and f.vix_rank > vix_max:
                return False
            vix_slope_min = conds.get("vix_slope_min")
            if vix_slope_min is not None and f.vix_slope < vix_slope_min:
                return False
            return True
        
        # 1) Prefer explicit per-regime conditions from config
        if matches_conditions("CHAOTIC"):
            return VolRegime.CHAOTIC
        if matches_conditions("HIGH_EVENT"):
            return VolRegime.HIGH_EVENT
        if matches_conditions("LOW_MEAN_REVERT"):
            return VolRegime.LOW_MEAN_REVERT
        if matches_conditions("MEDIUM_TREND"):
            return VolRegime.MEDIUM_TREND
        
        # 2) Fallback to coarse shared thresholds (backwards compatible)
        if (
            f.iv_rank >= th.get("high_iv_rank", 0.65)
            and f.atr_pct >= th.get("atr_pct_high", 1.50)
            and f.rv_iv_ratio >= th.get("rv_iv_high", 1.10)
        ):
            return VolRegime.CHAOTIC
        
        if (
            f.iv_rank >= th.get("high_iv_rank", 0.65)
            and f.vix_rank >= th.get("vix_extreme_rank", 0.80)
            and f.vix_slope >= th.get("vix_slope_up", 0.00)
        ):
            return VolRegime.HIGH_EVENT
        
        if (
            f.iv_rank <= th.get("low_iv_rank", 0.25)
            and f.atr_pct <= th.get("atr_pct_low", 0.40)
            and f.rv_iv_ratio <= th.get("rv_iv_low", 0.60)
        ):
            return VolRegime.LOW_MEAN_REVERT
        
        if (
            f.atr_pct >= th.get("atr_pct_low", 0.40)
            and f.atr_pct <= th.get("atr_pct_high", 1.50)
            and f.trend_strength >= th.get("trend_strength_min", 0.60)
        ):
            return VolRegime.MEDIUM_TREND
        
        return VolRegime.UNKNOWN


class RegimeVolEngine(Strategy):
    """
    Meta-strategy: decides WHICH child strategies (A–G) are allowed to fire,
    based on volatility regime.
    
    It does NOT generate structures directly; it delegates to existing
    strategy instances.
    """
    
    # Mapping from abstract "structure" to concrete child strategy key
    STRUCTURE_TO_STRATEGY = {
        "iron_condor": "IronCondor",
        "short_strangle": "OptionsRanker",  # Configure with short strangle params
        "directional_credit_spread": "OptionsRanker",  # Configure with credit spread params
        "index_sniper": "ORB",  # Opening Range Breakout
        "long_straddle": "OptionsRanker",  # Configure with long straddle params
        "stay_flat": None,
    }
    
    def __init__(
        self,
        name: str,
        params: Dict[str, Any],
        strategy_registry: Optional[Dict[str, Strategy]] = None,
        risk_engine: Optional[Any] = None,
        metrics: Optional[Any] = None,
    ):
        super().__init__(name, params)
        
        self.cfg = params
        self.shared_cfg = params.get("shared", {})
        self.regimes_cfg = params.get("regimes", {})
        self.underlyings = set(params.get("underlyings", []))
        
        self.classifier = RegimeClassifier(self.shared_cfg, self.regimes_cfg)
        self.registry = strategy_registry or {}
        self.risk = risk_engine
        self.metrics = metrics
        
        # Track daily trades per regime
        self.daily_trades_by_regime: Dict[str, int] = {}
        self.current_regime: Optional[VolRegime] = None
        
        # Log initialization
        logger.info(
            "RegimeVolEngine initialized",
            underlyings=list(self.underlyings),
            enabled=self.cfg.get("enabled", True),
            registry_keys=list(self.registry.keys())
        )
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """Generate signals by routing to appropriate strategies based on regime"""
        if not self.cfg.get("enabled", True):
            return []
        
        underlying = context.instrument.symbol
        if self.underlyings and underlying not in self.underlyings:
            return []
        
        # Adapt context to R1 interface
        ctx_adapter = MarketContextAdapter(context)
        
        # Compute features and classify regime
        try:
            feats = self.classifier.compute_features(ctx_adapter)
            regime = self.classifier.classify(feats)
            self.current_regime = regime
        except ZeroDivisionError as e:
            logger.error(
                "RegimeVolEngine feature computation failed (divide by zero)",
                underlying=underlying,
                error=str(e)
            )
            return []
        except Exception as e:
            logger.error(
                "RegimeVolEngine feature computation failed",
                underlying=underlying,
                error=str(e)
            )
            return []
        
        # Record metrics
        if self.metrics is not None:
            labels = {"underlying": underlying}
            
            # Numeric regime code (0-4)
            self.metrics.gauge("algo_vol_regime_code", labels).set(float(regime.value))
            
            # Feature gauges
            self.metrics.gauge("algo_vol_iv_rank", labels).set(feats.iv_rank)
            self.metrics.gauge("algo_vol_atr_pct", labels).set(feats.atr_pct)
            self.metrics.gauge("algo_vol_rv_iv_ratio", labels).set(feats.rv_iv_ratio)
            self.metrics.gauge("algo_vol_vix_rank", labels).set(feats.vix_rank)
            
            # One-hot regime flags for time-in-regime analysis
            for r in VolRegime:
                flag_labels = {**labels, "regime": r.name}
                value = 1.0 if r == regime else 0.0
                self.metrics.gauge("algo_vol_regime_flag", flag_labels).set(value)
        
        logger.debug(
            "Regime classified",
            underlying=underlying,
            regime=regime.name,
            iv_rank=feats.iv_rank,
            atr_pct=feats.atr_pct,
            trend_strength=feats.trend_strength
        )
        
        if regime == VolRegime.UNKNOWN:
            return []
        
        ideas: List[Signal] = []
        regime_cfg = self.regimes_cfg.get(regime.name, {})
        actions_cfg = regime_cfg.get("actions", {})
        
        max_daily_trades = actions_cfg.get("max_daily_trades", 0)
        max_capital_pct = actions_cfg.get("capital_pct", 0.0)
        
        structures = self._structures_for_regime(actions_cfg)
        for struct in structures:
            if struct == "stay_flat":
                continue
            
            strat = self._map_structure_to_strategy(struct)
            if strat is None:
                continue
            
            # Delegate to child strategy
            try:
                child_signals = strat.generate_signals(context) or []
                
                for signal in child_signals:
                    # Check risk allocation if risk engine available
                    if self.risk and hasattr(self.risk, 'can_allocate'):
                        if not self.risk.can_allocate(signal, max_capital_pct=max_capital_pct):
                            continue
                    
                    # Tag signal with regime info
                    signal.features = signal.features or {}
                    signal.features["regime"] = regime.name
                    signal.features["regime_iv_rank"] = feats.iv_rank
                    signal.features["regime_atr_pct"] = feats.atr_pct
                    signal.features["entry_regime"] = regime.name  # For PnL tracking
                    
                    ideas.append(signal)
                    
                    if len(ideas) >= max_daily_trades:
                        return ideas
            except Exception as e:
                logger.error(
                    "Error generating signals from child strategy",
                    structure=struct,
                    error=str(e)
                )
        
        return ideas
    
    @staticmethod
    def _structures_for_regime(actions_cfg: Dict[str, Any]) -> List[str]:
        """Get list of structures to try for a regime (de-duplicated)"""
        out: List[str] = []
        primary = actions_cfg.get("primary_structure")
        secondary = actions_cfg.get("secondary_structure")
        fallback = actions_cfg.get("fallback_structure")
        
        if primary:
            out.append(primary)
        if secondary:
            out.append(secondary)
        if fallback:
            out.append(fallback)
        
        # De-duplicate while preserving order
        seen = set()
        uniq: List[str] = []
        for s in out:
            if s not in seen:
                seen.add(s)
                uniq.append(s)
        return uniq
    
    def _map_structure_to_strategy(self, struct_name: str) -> Optional[Strategy]:
        """Map structure name to actual strategy instance"""
        strat_key = self.STRUCTURE_TO_STRATEGY.get(struct_name)
        if not strat_key:
            return None
        return self.registry.get(strat_key)
    
    def on_position_opened(self) -> None:
        """Track trades per regime when position opens"""
        super().on_position_opened()
        if self.current_regime:
            regime_key = f"unknown_{self.current_regime.name}"
            self.daily_trades_by_regime[regime_key] = self.daily_trades_by_regime.get(regime_key, 0) + 1
