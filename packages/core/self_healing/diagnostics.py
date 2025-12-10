"""
Self-Diagnostics Module
=======================

Detects trading anomalies and system health issues:
- Overtrading (too many signals/orders)
- Late entries (signals not filled quickly)
- Slippage issues (high slippage on fills)
- Catching falling knives (entries during downtrends)
- Strategy bias (certain strategies failing)
- Sideways market failures
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class AnomalyType(str, Enum):
    """Types of trading anomalies"""
    OVERTRADING = "OVERTRADING"
    LATE_ENTRIES = "LATE_ENTRIES"
    SLIPPAGE_ISSUES = "SLIPPAGE_ISSUES"
    FALLING_KNIVES = "FALLING_KNIVES"
    STRATEGY_BIAS = "STRATEGY_BIAS"
    SIDEWAYS_FAILURE = "SIDEWAYS_FAILURE"
    HIGH_REJECTION_RATE = "HIGH_REJECTION_RATE"
    EXECUTION_TIMEOUTS = "EXECUTION_TIMEOUTS"
    MARGIN_PRESSURE = "MARGIN_PRESSURE"
    LOW_WIN_RATE = "LOW_WIN_RATE"


@dataclass
class DiagnosticResult:
    """Result of a diagnostic check"""
    anomaly_type: AnomalyType
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    detected: bool
    score: float  # 0.0 to 1.0 (1.0 = most severe)
    message: str
    metrics: Dict[str, Any]
    recommended_actions: List[str]
    timestamp: datetime


class SelfDiagnostics:
    """
    Self-diagnostics engine that detects trading anomalies.
    
    Monitors:
    - Signal generation rate
    - Order fill latency
    - Slippage metrics
    - Win rate trends
    - Strategy performance
    - Market regime alignment
    """
    
    def __init__(
        self,
        signals_per_hour_threshold: int = 20,  # Alert if > 20 signals/hour
        fill_latency_threshold_ms: float = 5000.0,  # Alert if avg fill > 5s
        slippage_threshold_bps: float = 50.0,  # Alert if avg slippage > 50 bps
        min_win_rate: float = 0.40,  # Alert if win rate < 40%
        max_rejection_rate: float = 0.80,  # Alert if > 80% rejections
    ):
        """
        Initialize diagnostics engine.
        
        Args:
            signals_per_hour_threshold: Max signals per hour before overtrading alert
            fill_latency_threshold_ms: Max avg fill latency before late entry alert
            slippage_threshold_bps: Max avg slippage before slippage alert
            min_win_rate: Min win rate before low win rate alert
            max_rejection_rate: Max rejection rate before high rejection alert
        """
        self.signals_per_hour_threshold = signals_per_hour_threshold
        self.fill_latency_threshold_ms = fill_latency_threshold_ms
        self.slippage_threshold_bps = slippage_threshold_bps
        self.min_win_rate = min_win_rate
        self.max_rejection_rate = max_rejection_rate
        
        # History tracking
        self._signal_history: List[datetime] = []
        self._fill_history: List[Dict[str, Any]] = []
        self._slippage_history: List[float] = []
        self._rejection_history: List[Dict[str, Any]] = []
        
    def record_signal(self, timestamp: Optional[datetime] = None) -> None:
        """Record a signal generation event"""
        if timestamp is None:
            timestamp = datetime.now()
        self._signal_history.append(timestamp)
        # Keep only last 24 hours
        cutoff = timestamp - timedelta(hours=24)
        self._signal_history = [s for s in self._signal_history if s > cutoff]
    
    def record_fill(
        self,
        signal_time: datetime,
        fill_time: datetime,
        slippage_bps: float,
        strategy: str
    ) -> None:
        """Record an order fill event"""
        latency_ms = (fill_time - signal_time).total_seconds() * 1000
        self._fill_history.append({
            "signal_time": signal_time,
            "fill_time": fill_time,
            "latency_ms": latency_ms,
            "slippage_bps": slippage_bps,
            "strategy": strategy
        })
        self._slippage_history.append(slippage_bps)
        # Keep only last 100 fills
        if len(self._fill_history) > 100:
            self._fill_history.pop(0)
        if len(self._slippage_history) > 100:
            self._slippage_history.pop(0)
    
    def record_rejection(self, reason: str, strategy: str) -> None:
        """Record a rejection event"""
        self._rejection_history.append({
            "timestamp": datetime.now(),
            "reason": reason,
            "strategy": strategy
        })
        # Keep only last 1000 rejections
        if len(self._rejection_history) > 1000:
            self._rejection_history.pop(0)
    
    def run_diagnostics(
        self,
        current_metrics: Dict[str, Any],
        strategy_performance: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[DiagnosticResult]:
        """
        Run all diagnostic checks.
        
        Args:
            current_metrics: Current system metrics (from API/state)
            strategy_performance: Per-strategy performance metrics
            
        Returns:
            List of diagnostic results (anomalies detected)
        """
        results = []
        
        # Check overtrading
        results.append(self._check_overtrading())
        
        # Check late entries
        results.append(self._check_late_entries())
        
        # Check slippage
        results.append(self._check_slippage())
        
        # Check win rate
        results.append(self._check_win_rate(current_metrics))
        
        # Check rejection rate
        results.append(self._check_rejection_rate())
        
        # Check strategy bias
        if strategy_performance:
            results.append(self._check_strategy_bias(strategy_performance))
        
        # Check margin pressure
        results.append(self._check_margin_pressure(current_metrics))
        
        # Filter to only detected anomalies
        return [r for r in results if r.detected]
    
    def _check_overtrading(self) -> DiagnosticResult:
        """Check for overtrading (too many signals)"""
        if not self._signal_history:
            return DiagnosticResult(
                anomaly_type=AnomalyType.OVERTRADING,
                severity="LOW",
                detected=False,
                score=0.0,
                message="No signals recorded",
                metrics={},
                recommended_actions=[],
                timestamp=datetime.now()
            )
        
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        signals_last_hour = sum(1 for s in self._signal_history if s > last_hour)
        
        detected = signals_last_hour > self.signals_per_hour_threshold
        score = min(1.0, signals_last_hour / (self.signals_per_hour_threshold * 2))
        
        if detected:
            severity = "HIGH" if signals_last_hour > self.signals_per_hour_threshold * 1.5 else "MEDIUM"
            return DiagnosticResult(
                anomaly_type=AnomalyType.OVERTRADING,
                severity=severity,
                detected=True,
                score=score,
                message=f"Overtrading detected: {signals_last_hour} signals in last hour (threshold: {self.signals_per_hour_threshold})",
                metrics={"signals_last_hour": signals_last_hour, "threshold": self.signals_per_hour_threshold},
                recommended_actions=[
                    "Reduce signal generation frequency",
                    "Increase signal filters strictness",
                    "Pause trading temporarily"
                ],
                timestamp=datetime.now()
            )
        
        return DiagnosticResult(
            anomaly_type=AnomalyType.OVERTRADING,
            severity="LOW",
            detected=False,
            score=0.0,
            message=f"Signal rate normal: {signals_last_hour} signals/hour",
            metrics={"signals_last_hour": signals_last_hour},
            recommended_actions=[],
            timestamp=datetime.now()
        )
    
    def _check_late_entries(self) -> DiagnosticResult:
        """Check for late entries (slow order fills)"""
        if not self._fill_history:
            return DiagnosticResult(
                anomaly_type=AnomalyType.LATE_ENTRIES,
                severity="LOW",
                detected=False,
                score=0.0,
                message="No fills recorded",
                metrics={},
                recommended_actions=[],
                timestamp=datetime.now()
            )
        
        avg_latency = sum(f["latency_ms"] for f in self._fill_history) / len(self._fill_history)
        detected = avg_latency > self.fill_latency_threshold_ms
        score = min(1.0, avg_latency / (self.fill_latency_threshold_ms * 2))
        
        if detected:
            severity = "HIGH" if avg_latency > self.fill_latency_threshold_ms * 2 else "MEDIUM"
            return DiagnosticResult(
                anomaly_type=AnomalyType.LATE_ENTRIES,
                severity=severity,
                detected=True,
                score=score,
                message=f"Late entries detected: avg fill latency {avg_latency:.0f}ms (threshold: {self.fill_latency_threshold_ms:.0f}ms)",
                metrics={"avg_latency_ms": avg_latency, "threshold_ms": self.fill_latency_threshold_ms},
                recommended_actions=[
                    "Increase limit chase aggressiveness",
                    "Use market orders for time-sensitive entries",
                    "Reduce order complexity"
                ],
                timestamp=datetime.now()
            )
        
        return DiagnosticResult(
            anomaly_type=AnomalyType.LATE_ENTRIES,
            severity="LOW",
            detected=False,
            score=0.0,
            message=f"Fill latency normal: {avg_latency:.0f}ms",
            metrics={"avg_latency_ms": avg_latency},
            recommended_actions=[],
            timestamp=datetime.now()
        )
    
    def _check_slippage(self) -> DiagnosticResult:
        """Check for slippage issues"""
        if not self._slippage_history:
            return DiagnosticResult(
                anomaly_type=AnomalyType.SLIPPAGE_ISSUES,
                severity="LOW",
                detected=False,
                score=0.0,
                message="No slippage data",
                metrics={},
                recommended_actions=[],
                timestamp=datetime.now()
            )
        
        avg_slippage = sum(self._slippage_history) / len(self._slippage_history)
        detected = avg_slippage > self.slippage_threshold_bps
        score = min(1.0, avg_slippage / (self.slippage_threshold_bps * 2))
        
        if detected:
            severity = "HIGH" if avg_slippage > self.slippage_threshold_bps * 2 else "MEDIUM"
            return DiagnosticResult(
                anomaly_type=AnomalyType.SLIPPAGE_ISSUES,
                severity=severity,
                detected=True,
                score=score,
                message=f"High slippage detected: avg {avg_slippage:.1f} bps (threshold: {self.slippage_threshold_bps:.1f} bps)",
                metrics={"avg_slippage_bps": avg_slippage, "threshold_bps": self.slippage_threshold_bps},
                recommended_actions=[
                    "Reduce position sizes",
                    "Trade only high-liquidity instruments",
                    "Increase limit chase max slippage tolerance"
                ],
                timestamp=datetime.now()
            )
        
        return DiagnosticResult(
            anomaly_type=AnomalyType.SLIPPAGE_ISSUES,
            severity="LOW",
            detected=False,
            score=0.0,
            message=f"Slippage normal: {avg_slippage:.1f} bps",
            metrics={"avg_slippage_bps": avg_slippage},
            recommended_actions=[],
            timestamp=datetime.now()
        )
    
    def _check_win_rate(self, metrics: Dict[str, Any]) -> DiagnosticResult:
        """Check for low win rate"""
        win_rate = metrics.get("win_rate", 0.0)
        trades_today = metrics.get("trades_today", 0)
        
        if trades_today < 5:  # Need minimum trades for meaningful win rate
            return DiagnosticResult(
                anomaly_type=AnomalyType.LOW_WIN_RATE,
                severity="LOW",
                detected=False,
                score=0.0,
                message=f"Insufficient trades for win rate check: {trades_today} trades",
                metrics={"trades_today": trades_today, "win_rate": win_rate},
                recommended_actions=[],
                timestamp=datetime.now()
            )
        
        detected = win_rate < self.min_win_rate
        score = max(0.0, (self.min_win_rate - win_rate) / self.min_win_rate) if detected else 0.0
        
        if detected:
            severity = "CRITICAL" if win_rate < self.min_win_rate * 0.5 else "HIGH"
            return DiagnosticResult(
                anomaly_type=AnomalyType.LOW_WIN_RATE,
                severity=severity,
                detected=True,
                score=score,
                message=f"Low win rate detected: {win_rate:.1%} (threshold: {self.min_win_rate:.1%})",
                metrics={"win_rate": win_rate, "trades_today": trades_today, "threshold": self.min_win_rate},
                recommended_actions=[
                    "Review strategy filters",
                    "Reduce position sizes",
                    "Consider pausing underperforming strategies"
                ],
                timestamp=datetime.now()
            )
        
        return DiagnosticResult(
            anomaly_type=AnomalyType.LOW_WIN_RATE,
            severity="LOW",
            detected=False,
            score=0.0,
            message=f"Win rate acceptable: {win_rate:.1%}",
            metrics={"win_rate": win_rate, "trades_today": trades_today},
            recommended_actions=[],
            timestamp=datetime.now()
        )
    
    def _check_rejection_rate(self) -> DiagnosticResult:
        """Check for high rejection rate"""
        if not self._rejection_history:
            return DiagnosticResult(
                anomaly_type=AnomalyType.HIGH_REJECTION_RATE,
                severity="LOW",
                detected=False,
                score=0.0,
                message="No rejections recorded",
                metrics={},
                recommended_actions=[],
                timestamp=datetime.now()
            )
        
        # Count rejections in last hour
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        recent_rejections = [r for r in self._rejection_history if r["timestamp"] > last_hour]
        
        # Estimate total signals (rejections + fills)
        total_signals = len(recent_rejections) + len([f for f in self._fill_history if f["signal_time"] > last_hour])
        
        if total_signals == 0:
            return DiagnosticResult(
                anomaly_type=AnomalyType.HIGH_REJECTION_RATE,
                severity="LOW",
                detected=False,
                score=0.0,
                message="No signals in last hour",
                metrics={},
                recommended_actions=[],
                timestamp=datetime.now()
            )
        
        rejection_rate = len(recent_rejections) / total_signals
        detected = rejection_rate > self.max_rejection_rate
        score = min(1.0, rejection_rate / self.max_rejection_rate) if detected else 0.0
        
        if detected:
            severity = "HIGH" if rejection_rate > 0.90 else "MEDIUM"
            return DiagnosticResult(
                anomaly_type=AnomalyType.HIGH_REJECTION_RATE,
                severity=severity,
                detected=True,
                score=score,
                message=f"High rejection rate: {rejection_rate:.1%} (threshold: {self.max_rejection_rate:.1%})",
                metrics={"rejection_rate": rejection_rate, "rejections": len(recent_rejections), "total_signals": total_signals},
                recommended_actions=[
                    "Review rejection reasons",
                    "Relax filters if too strict",
                    "Check risk limits"
                ],
                timestamp=datetime.now()
            )
        
        return DiagnosticResult(
            anomaly_type=AnomalyType.HIGH_REJECTION_RATE,
            severity="LOW",
            detected=False,
            score=0.0,
            message=f"Rejection rate normal: {rejection_rate:.1%}",
            metrics={"rejection_rate": rejection_rate},
            recommended_actions=[],
            timestamp=datetime.now()
        )
    
    def _check_strategy_bias(self, strategy_performance: Dict[str, Dict[str, Any]]) -> DiagnosticResult:
        """Check for strategy bias (certain strategies consistently failing)"""
        failing_strategies = []
        
        for strategy_name, perf in strategy_performance.items():
            win_rate = perf.get("win_rate", 0.0)
            trades = perf.get("trades", 0)
            
            if trades >= 3 and win_rate < self.min_win_rate:
                failing_strategies.append({
                    "strategy": strategy_name,
                    "win_rate": win_rate,
                    "trades": trades
                })
        
        if failing_strategies:
            return DiagnosticResult(
                anomaly_type=AnomalyType.STRATEGY_BIAS,
                severity="MEDIUM",
                detected=True,
                score=len(failing_strategies) / 10.0,  # Normalize by max expected strategies
                message=f"Strategy bias detected: {len(failing_strategies)} strategies underperforming",
                metrics={"failing_strategies": failing_strategies},
                recommended_actions=[
                    "Disable underperforming strategies",
                    "Reduce allocation to failing strategies",
                    "Review strategy parameters"
                ],
                timestamp=datetime.now()
            )
        
        return DiagnosticResult(
            anomaly_type=AnomalyType.STRATEGY_BIAS,
            severity="LOW",
            detected=False,
            score=0.0,
            message="No strategy bias detected",
            metrics={},
            recommended_actions=[],
            timestamp=datetime.now()
        )
    
    def _check_margin_pressure(self, metrics: Dict[str, Any]) -> DiagnosticResult:
        """Check for margin pressure"""
        margin_utilization = metrics.get("margin_utilization", 0.0)
        margin_threshold = 0.70  # 70% utilization
        
        detected = margin_utilization > margin_threshold
        score = min(1.0, margin_utilization / margin_threshold) if detected else 0.0
        
        if detected:
            severity = "CRITICAL" if margin_utilization > 0.90 else "HIGH"
            return DiagnosticResult(
                anomaly_type=AnomalyType.MARGIN_PRESSURE,
                severity=severity,
                detected=True,
                score=score,
                message=f"Margin pressure detected: {margin_utilization:.1%} utilization (threshold: {margin_threshold:.1%})",
                metrics={"margin_utilization": margin_utilization, "threshold": margin_threshold},
                recommended_actions=[
                    "Reduce position sizes",
                    "Close some positions",
                    "Increase margin buffer"
                ],
                timestamp=datetime.now()
            )
        
        return DiagnosticResult(
            anomaly_type=AnomalyType.MARGIN_PRESSURE,
            severity="LOW",
            detected=False,
            score=0.0,
            message=f"Margin utilization normal: {margin_utilization:.1%}",
            metrics={"margin_utilization": margin_utilization},
            recommended_actions=[],
            timestamp=datetime.now()
        )





