"""Event-Driven Volatility Engine (E1) - Context engine for event-aware adjustments"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class EventDef:
    """Event definition from config"""
    name: str
    type: str
    underlyings: List[str]
    dates: List[date]
    pre_event_days: int
    post_event_days: int
    severity: float


@dataclass
class DayContext:
    """Day context for a specific underlying"""
    day: date
    underlying: str
    day_type: str  # "NORMAL", "PRE_EVENT", "EVENT_DAY", "POST_EVENT"
    primary_event: Optional[str]
    primary_type: Optional[str]
    severity: float
    r1_regime_bias: Dict[str, float]
    allocator_role_multipliers: Dict[str, float]
    h1_coverage_multiplier: float


class EventVolEngine:
    """
    Event-Driven Volatility Engine (E1).
    
    Precomputes day context (NORMAL / PRE_EVENT / EVENT_DAY / POST_EVENT)
    and provides overlays for R1, Allocator, and H1.
    
    This is a context engine, not a trading strategy.
    """
    
    def __init__(self, cfg: Dict[str, Any], metrics: Optional[Any] = None):
        self.cfg = cfg
        self.enabled = cfg.get("enabled", True)
        self.tz = cfg.get("timezone", "Asia/Kolkata")
        self.defaults = cfg.get("defaults", {})
        self.day_type_overlays = cfg.get("day_type_overlays", {})
        self.metrics = metrics
        
        self.events: List[EventDef] = self._parse_events(cfg.get("calendar", []))
        
        # Cache: (date, underlying) -> DayContext
        self._cache: Dict[tuple[date, str], DayContext] = {}
        
        logger.info(
            "EventVolEngine initialized",
            enabled=self.enabled,
            num_events=len(self.events)
        )
    
    # ------------------------------------------------------------------ config parsing
    
    def _parse_events(self, items: List[Dict[str, Any]]) -> List[EventDef]:
        """Parse event definitions from config"""
        out: List[EventDef] = []
        
        for item in items:
            ev_dates = []
            for ds in item.get("dates", []):
                try:
                    ev_dates.append(date.fromisoformat(ds))
                except Exception as e:
                    logger.warning("Invalid event date", date_str=ds, error=str(e))
                    continue
            
            if not ev_dates:
                continue
            
            out.append(
                EventDef(
                    name=item["name"],
                    type=item.get("type", "GENERIC"),
                    underlyings=item.get("underlyings", []),
                    dates=ev_dates,
                    pre_event_days=int(item.get("pre_event_days", 0)),
                    post_event_days=int(item.get("post_event_days", 0)),
                    severity=float(item.get("severity", 0.5)),
                )
            )
        
        return out
    
    # ------------------------------------------------------------------ public API
    
    def get_day_context(self, day: date, underlying: str) -> DayContext:
        """
        Main entry for other components (R1, allocator, H1).
        
        Returns DayContext with day_type, overlays, etc.
        """
        if not self.enabled:
            return self._get_default_context(day, underlying)
        
        key = (day, underlying)
        if key not in self._cache:
            self._cache[key] = self._compute_day_context(day, underlying)
        
        ctx = self._cache[key]
        
        # Export metrics
        if self.metrics:
            labels = {"underlying": underlying, "day_type": ctx.day_type}
            self.metrics.gauge("event_vol_severity", labels).set(ctx.severity)
            self.metrics.gauge("event_vol_is_event_day", labels).set(1.0 if ctx.day_type == "EVENT_DAY" else 0.0)
            
            # One-hot flags for day types
            for dt in ["NORMAL", "PRE_EVENT", "EVENT_DAY", "POST_EVENT"]:
                flag_labels = {**labels, "day_type_flag": dt}
                value = 1.0 if ctx.day_type == dt else 0.0
                self.metrics.gauge("event_vol_day_type_flag", flag_labels).set(value)
        
        return ctx
    
    def get_today_context(self, underlying: str, now: Optional[datetime] = None) -> DayContext:
        """Get context for today"""
        if now is None:
            now = datetime.now()
        return self.get_day_context(now.date(), underlying)
    
    def _get_default_context(self, day: date, underlying: str) -> DayContext:
        """Return default NORMAL context when disabled"""
        overlay = self.day_type_overlays.get("NORMAL", {})
        return DayContext(
            day=day,
            underlying=underlying,
            day_type="NORMAL",
            primary_event=None,
            primary_type=None,
            severity=0.0,
            r1_regime_bias=overlay.get("r1_regime_bias", {}),
            allocator_role_multipliers=overlay.get("allocator_role_multipliers", {}),
            h1_coverage_multiplier=float(overlay.get("h1_coverage_multiplier", 1.0)),
        )
    
    # ------------------------------------------------------------------ core logic
    
    def _compute_day_context(self, d: date, underlying: str) -> DayContext:
        """Compute day context for a specific date and underlying"""
        # Find relevant events for this underlying and date
        candidates = []
        
        for ev in self.events:
            if underlying not in ev.underlyings:
                continue
            
            for ev_day in ev.dates:
                delta = (d - ev_day).days
                
                if delta == 0:
                    # Event day
                    candidates.append((ev, "EVENT_DAY", 0))
                elif -ev.pre_event_days <= delta < 0:
                    # Pre-event window
                    candidates.append((ev, "PRE_EVENT", abs(delta)))
                elif 0 < delta <= ev.post_event_days:
                    # Post-event window
                    candidates.append((ev, "POST_EVENT", delta))
        
        # Choose most severe / closest event if multiple
        primary_ev: Optional[EventDef] = None
        day_type = self.defaults.get("day_type", "NORMAL")
        severity = 0.0
        
        if candidates:
            # Sort by severity desc, then distance asc
            candidates.sort(key=lambda x: (-x[0].severity, x[2]))
            primary_ev, day_type_candidate, _dist = candidates[0]
            day_type = day_type_candidate
            severity = primary_ev.severity
        else:
            primary_ev = None
            day_type = "NORMAL"
            severity = 0.0
        
        # Post-filter by minimum severity thresholds
        min_ev = float(self.defaults.get("min_severity_for_event_day", 0.5))
        min_prepost = float(self.defaults.get("min_severity_for_pre_post", 0.3))
        
        if day_type == "EVENT_DAY" and severity < min_ev:
            day_type = "NORMAL"
            primary_ev = None
            severity = 0.0
        
        if day_type in ("PRE_EVENT", "POST_EVENT") and severity < min_prepost:
            day_type = "NORMAL"
            primary_ev = None
            severity = 0.0
        
        # Get overlay for day type
        overlay = self.day_type_overlays.get(day_type, self.day_type_overlays.get("NORMAL", {}))
        
        r1_bias = overlay.get("r1_regime_bias", {})
        alloc_mult = overlay.get("allocator_role_multipliers", {})
        h1_mult = float(overlay.get("h1_coverage_multiplier", 1.0))
        
        return DayContext(
            day=d,
            underlying=underlying,
            day_type=day_type,
            primary_event=primary_ev.name if primary_ev else None,
            primary_type=primary_ev.type if primary_ev else None,
            severity=severity,
            r1_regime_bias=r1_bias,
            allocator_role_multipliers=alloc_mult,
            h1_coverage_multiplier=h1_mult,
        )


