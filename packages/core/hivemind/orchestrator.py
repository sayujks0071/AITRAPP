"""
HiveMind Orchestrator - Agent-to-Agent Interaction Loop
=======================================================

Simple multi-agent loop for collaborative decision-making:
- AnalystAgent proposes changes
- SG1StrategyGenerator turns insights into concrete patches
- RiskAgent critiques and approves/rejects

All agents share the same LLM backend (Claude or OpenAI).
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional

from packages.core.hivemind.base import BaseAgent
from packages.core.intelligence.llm_client import LLMClient, LLMConfig
from packages.core.intelligence.analyst import CortexAnalyst
from packages.core.intelligence.sg1 import SG1StrategyGenerator

logger = None
try:
    import logging
    logger = logging.getLogger("hivemind.orchestrator")
except:
    pass


class HiveMindOrchestrator:
    """
    Simple multi-agent loop:

      - CortexAnalyst proposes changes
      - SG1StrategyGenerator turns consensus into patches/commands
      - (Future: RiskOfficerAgent critiques)

    All agents share the same LLM backend (Claude/OpenAI).
    """

    def __init__(self, vector_store=None):
        """
        Initialize orchestrator with shared LLM client.
        
        Args:
            vector_store: Optional vector store for RAG (can be None for now)
        """
        # Shared LLM client - all agents use the same backend
        llm = LLMClient(LLMConfig())
        
        self.vector_store = vector_store

        # Initialize agents with shared LLM client
        self.analyst = CortexAnalyst(vector_store=vector_store, llm_client=llm)
        self.sg1 = SG1StrategyGenerator(vector_store=vector_store, llm_client=llm)

    def run_config_round(self, core_ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        One full 'conversation' round among agents over Claude/OpenAI.

        Args:
            core_ctx: Core context with metrics, guardrails, etc.
                Example:
                {
                    "day": "2025-11-21",
                    "metrics": {
                        "intraday_short_strangle_v1": {
                            "trades": 4, "wins": 3, "losses": 1, "max_dd": -2800
                        },
                        "trend_credit_spread_v1": {
                            "trades": 2, "wins": 1, "losses": 1, "max_dd": -1900
                        }
                    },
                    "guardrails": {
                        "max_dd_per_strategy": 0.03,
                        "max_dd_portfolio": 0.05,
                    }
                }

        Returns:
            Dict with outputs from all agents:
            {
                "analyst": {...},
                "sg1": {...},
            }
        """
        # 1) Analyst: read metrics + RAG, propose changes
        analyst_ctx = {
            "query": "Summarise today and propose safe config tweaks.",
            "core": core_ctx,
            "rag_source": None,
        }
        analyst_out = self.analyst.think(analyst_ctx)

        # 2) Strategy Generator: turn that into concrete patches
        sg1_ctx = {
            "query": "Convert analyst insights into concrete AITRAPP strategy patches.",
            "core": {
                "analyst": analyst_out,
                "metrics": core_ctx.get("metrics", {}),
            },
        }
        sg1_out = self.sg1.think(sg1_ctx)

        return {
            "analyst": analyst_out,
            "sg1": sg1_out,
        }




