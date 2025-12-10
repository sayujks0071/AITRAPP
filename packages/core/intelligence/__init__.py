"""
AI Intelligence Module
=====================

Self-evolving trading system components:
- AI Analyst: End-of-day analysis and config evolution
- RAG Memory: Historical episode storage and retrieval
- Log Parser: Extracts metrics from trading logs
- Cortex: High-level self-evolving intelligence orchestrator
- SG-1: Strategy Generator 1 (Level 6 - Self-Replicating)
- SME: Strategic Memory Engine (Level 8 - Institutional Memory)
"""

from packages.core.intelligence.ai_analyst import AIAnalyst
from packages.core.intelligence.log_parser import LogParser
from packages.core.intelligence.cortex import Cortex
from packages.core.intelligence.sg1 import SG1Generator, SG1StrategyGenerator
from packages.core.intelligence.analyst import CortexAnalyst
from packages.core.intelligence.sme import StrategicMemoryEngine

__all__ = [
    "AIAnalyst", 
    "LogParser", 
    "Cortex", 
    "SG1Generator", 
    "SG1StrategyGenerator",
    "CortexAnalyst",
    "StrategicMemoryEngine"
]

