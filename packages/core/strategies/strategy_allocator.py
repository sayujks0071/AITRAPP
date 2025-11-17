"""Multi-Strategy Allocator - Fund-of-strategies layer that allocates capital"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class StrategyStatsSnapshot:
    """Snapshot of strategy performance stats"""
    hit_rate: float
    expectancy_perc: float
    max_drawdown_perc: float
    recent_loss_streak: int
    num_trades_window: int


@dataclass
class StrategyAlloc:
    """Allocation for a strategy"""
    name: str
    enabled: bool
    base_weight: float
    raw_score: float
    final_weight: float
    max_capital_pct: float


class StrategyAllocator:
    """
    Meta-layer that computes per-strategy capital caps.
    
    Does NOT generate trades; it updates risk_engine state and emits metrics.
    
    Can run rule-based today, swap in ML later without changing wiring.
    """
    
    def __init__(
        self,
        cfg: Dict[str, Any],
        risk_engine: Any,
        stats_engine: Any,
        metrics: Optional[Any] = None,
    ) -> None:
        self.cfg = cfg
        self.thresholds = cfg.get("thresholds", {})
        self.stats_cfg = cfg.get("stats", {})
        self.regime_overlays = cfg.get("regime_overlays", {})
        self.risk_engine = risk_engine
        self.stats_engine = stats_engine
        self.metrics = metrics
        
        self.strategy_cfgs = cfg.get("strategies", [])
        
        logger.info(
            "StrategyAllocator initialized",
            num_strategies=len(self.strategy_cfgs),
            enabled=cfg.get("enabled", True)
        )
    
    def run_allocation_cycle(
        self,
        current_regime: Optional[str] = None,
        event_ctx: Optional[Any] = None
    ) -> Dict[str, StrategyAlloc]:
        """
        Called periodically (e.g. once at start-of-day, or every N minutes).
        
        Returns dict of allocations and updates risk_engine caps.
        
        Args:
            current_regime: Current R1 regime (e.g. "LOW_MEAN_REVERT", "MEDIUM_TREND")
            event_ctx: Event context from E1 (DayContext object)
        
        Returns:
            Dict mapping strategy name to StrategyAlloc
        """
        if not self.cfg.get("enabled", True):
            logger.debug("StrategyAllocator disabled")
            return {}
        
        stats_window_trades = self.stats_cfg.get("trade_window", 50)
        stats_window_days = self.stats_cfg.get("day_window", 30)
        
        # 1) Gather stats + compute raw scores
        allocs: Dict[str, StrategyAlloc] = {}
        
        for sc in self.strategy_cfgs:
            name = sc.get("name")
            if not name:
                continue
            
            base_weight = sc.get("base_weight", 0.1)
            
            stats = self._get_stats(name, stats_window_trades, stats_window_days)
            enabled, raw_score = self._score_strategy(name, sc, stats)
            
            allocs[name] = StrategyAlloc(
                name=name,
                enabled=enabled,
                base_weight=base_weight,
                raw_score=raw_score,
                final_weight=0.0,  # Filled later
                max_capital_pct=0.0,  # Filled later
            )
        
        # 2) Apply regime overlay and event overlay, then normalize weights
        if current_regime:
            self._apply_regime_overlay(allocs, current_regime)
        if event_ctx:
            self._apply_event_overlay(allocs, event_ctx)
        self._normalise_weights(allocs)
        
        # 3) Derive capital caps and update risk engine
        global_cap = self.cfg.get("global_max_capital_pct", 0.60)
        cap_min = self.cfg.get("min_capital_pct_per_strategy", 0.01)
        cap_max = self.cfg.get("max_capital_pct_per_strategy", 0.25)
        
        for alloc in allocs.values():
            if not alloc.enabled or alloc.final_weight <= 0.0:
                alloc.max_capital_pct = 0.0
            else:
                cap = alloc.final_weight * global_cap
                cap = max(min(cap, cap_max), cap_min)
                alloc.max_capital_pct = cap
            
            # Update risk engine
            if hasattr(self.risk_engine, 'set_strategy_cap'):
                self.risk_engine.set_strategy_cap(alloc.name, alloc.max_capital_pct)
            
            # Emit metrics
            if self.metrics:
                labels = {"strategy": alloc.name}
                self.metrics.gauge("allocator_raw_score", labels).set(alloc.raw_score)
                self.metrics.gauge("allocator_final_weight", labels).set(alloc.final_weight)
                self.metrics.gauge("allocator_max_capital_pct", labels).set(alloc.max_capital_pct)
                self.metrics.gauge("allocator_enabled", labels).set(1.0 if alloc.enabled else 0.0)
        
        logger.info(
            "Allocation cycle completed",
            num_strategies=len(allocs),
            regime=current_regime or "UNKNOWN"
        )
        
        return allocs
    
    def _get_stats(
        self,
        strategy_name: str,
        trade_window: int,
        day_window: int
    ) -> StrategyStatsSnapshot:
        """Get stats from stats engine"""
        try:
            stats = self.stats_engine.get_stats(
                strategy_name,
                trade_window=trade_window,
                day_window=day_window
            )
            return StrategyStatsSnapshot(
                hit_rate=stats.hit_rate,
                expectancy_perc=stats.expectancy_perc,
                max_drawdown_perc=stats.max_drawdown_perc,
                recent_loss_streak=stats.recent_loss_streak,
                num_trades_window=stats.num_trades_window,
            )
        except Exception as e:
            logger.error("Error getting stats", strategy=strategy_name, error=str(e))
            return StrategyStatsSnapshot(
                hit_rate=0.5,
                expectancy_perc=0.0,
                max_drawdown_perc=0.0,
                recent_loss_streak=0,
                num_trades_window=0,
            )
    
    def _score_strategy(
        self,
        name: str,
        sc: Dict[str, Any],
        stats: StrategyStatsSnapshot,
    ) -> tuple[bool, float]:
        """
        Scoring: 0–1 scale.
        
        If an ML scorer is configured and available on the stats_engine
        (get_ml_score), use that; otherwise fall back to the rule-based
        heuristic. This allows swapping in a learned model without changing
        allocator wiring.
        
        Later you can replace this with an ML call that returns a score.
        
        Returns:
            (enabled: bool, score: float)
        """
        th = self.thresholds
        
        # 0) Optional ML-based score
        ml_cfg = self.cfg.get("ml", {})
        if ml_cfg.get("enabled", False) and hasattr(self.stats_engine, "get_ml_score"):
            try:
                ml_score = float(
                    self.stats_engine.get_ml_score(
                        name,
                        {
                            "hit_rate": stats.hit_rate,
                            "expectancy_perc": stats.expectancy_perc,
                            "max_drawdown_perc": stats.max_drawdown_perc,
                            "recent_loss_streak": stats.recent_loss_streak,
                            "num_trades_window": stats.num_trades_window,
                        },
                    )
                )
                ml_score = max(0.0, min(ml_score, 1.0))
                enabled = True if ml_score > 0.0 else False
                return enabled, ml_score
            except Exception as e:
                logger.warning("ML scorer failed, falling back to rules", strategy=name, error=str(e))
        
        # Basic health checks
        if stats.num_trades_window < max(5, th.get("cold_streak_trades", 7)):
            # Not enough data → keep enabled but low score
            enabled = True
            return enabled, 0.3
        
        if stats.max_drawdown_perc > th.get("max_drawdown_perc", 5.0):
            # Deep drawdown → maybe disable
            enabled = False
            return enabled, 0.0
        
        if stats.recent_loss_streak >= th.get("cold_streak_trades", 7):
            enabled = False
            return enabled, 0.0
        
        # Score components
        score = 0.0
        
        # Hit rate contribution
        hr = stats.hit_rate
        min_hr = th.get("min_hit_rate", 0.45)
        if hr >= min_hr:
            # Map [min_hit_rate, 1] -> [0.4, 0.9]
            score += 0.4 + 0.5 * ((hr - min_hr) / max(1e-6, 1.0 - min_hr))
        else:
            # Below threshold → small positive, not zero
            score += 0.1 * (hr / max(1e-6, min_hr))
        
        # Expectancy contribution
        exp = stats.expectancy_perc
        min_exp = th.get("min_expectancy_perc", 0.10)
        if exp >= min_exp:
            score += 0.3
        else:
            score += 0.1 * max(0.0, exp / max(1e-6, min_exp))
        
        # Drawdown penalty
        dd = stats.max_drawdown_perc
        max_dd = th.get("max_drawdown_perc", 5.0)
        dd_penalty = min(dd / (max_dd * 2.0), 1.0)
        score *= (1.0 - 0.5 * dd_penalty)
        
        # Ensure [0, 1]
        score = max(0.0, min(score, 1.0))
        enabled = True
        
        return enabled, score
    
    def _apply_regime_overlay(self, allocs: Dict[str, StrategyAlloc], regime: str) -> None:
        """
        Adjust scores based on current vol regime and strategy role.
        """
        overlay = self.regime_overlays.get(regime)
        if not overlay:
            return
        
        boost_roles = set(overlay.get("boost_roles", []))
        cut_roles = set(overlay.get("cut_roles", []))
        
        for sc in self.strategy_cfgs:
            name = sc.get("name")
            if not name or name not in allocs:
                continue
            
            role = sc.get("role", "")
            alloc = allocs[name]
            
            if role in boost_roles:
                alloc.raw_score *= 1.2
            if role in cut_roles:
                alloc.raw_score *= 0.7
            
            alloc.raw_score = max(0.0, min(alloc.raw_score, 1.0))
    
    def _apply_event_overlay(self, allocs: Dict[str, StrategyAlloc], event_ctx: Any) -> None:
        """
        Adjust scores based on event context (E1).
        
        Args:
            allocs: Strategy allocations to adjust
            event_ctx: DayContext from EventVolEngine
        """
        multipliers = event_ctx.allocator_role_multipliers
        if not multipliers:
            return
        
        for sc in self.strategy_cfgs:
            name = sc.get("name")
            if not name or name not in allocs:
                continue
            
            role = sc.get("role", "")
            if role in multipliers:
                mult = multipliers[role]
                alloc = allocs[name]
                alloc.raw_score *= mult
                alloc.raw_score = max(0.0, min(alloc.raw_score, 1.0))
    
    def _normalise_weights(self, allocs: Dict[str, StrategyAlloc]) -> None:
        """
        Convert raw scores + base weights into final weights that sum to <= 1.
        """
        # Combine base_weight and score multiplicatively
        tmp: Dict[str, float] = {}
        for sc in self.strategy_cfgs:
            name = sc.get("name")
            if not name or name not in allocs:
                continue
            
            bw = sc.get("base_weight", 0.1)
            alloc = allocs[name]
            
            if not alloc.enabled or alloc.raw_score <= 0.0:
                tmp[name] = 0.0
            else:
                tmp[name] = bw * alloc.raw_score
        
        total = sum(tmp.values())
        if total <= 0.0:
            # Nobody is good → equal small weights or all zero
            for sc in self.strategy_cfgs:
                name = sc.get("name")
                if name in allocs:
                    allocs[name].final_weight = 0.0
            return
        
        for sc in self.strategy_cfgs:
            name = sc.get("name")
            if name in allocs:
                allocs[name].final_weight = tmp[name] / total
