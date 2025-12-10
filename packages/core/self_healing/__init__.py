"""
Self-Diagnostics + Self-Healing System
======================================

Automatically detects trading anomalies and applies corrective actions.

Components:
- SelfDiagnostics: Detects problems (overtrading, slippage, late entries, etc.)
- SelfHealing: Applies corrective actions (strategy switching, size reduction, etc.)
- HealingHistory: Tracks healing events in RAG Memory
"""

from packages.core.self_healing.diagnostics import SelfDiagnostics, DiagnosticResult, AnomalyType
from packages.core.self_healing.healing import SelfHealing, HealingAction, HealingResult

__all__ = [
    "SelfDiagnostics",
    "DiagnosticResult",
    "AnomalyType",
    "SelfHealing",
    "HealingAction",
    "HealingResult"
]





