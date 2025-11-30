"""
Reflex System - Level 8
=======================

Zero-latency emergency response system for flash crash protection.

While the HiveMind (Level 7) "thinks" about decisions (which takes seconds),
the Reflex System "reacts" to danger (which takes milliseconds).

Components:
- MAD-1: Market Anomaly Detection (crash detector)
- EmergencyBrake: Instant position liquidation
- ReflexSystem: Connects MAD-1 to Brake
"""

from packages.core.reflex.engine import ReflexSystem
from packages.core.reflex.mad1 import MAD1
from packages.core.reflex.brake import EmergencyBrake

__all__ = ["ReflexSystem", "MAD1", "EmergencyBrake"]

