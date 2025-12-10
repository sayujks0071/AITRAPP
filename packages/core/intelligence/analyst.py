"""
Cortex Analyst - HiveMind Post-Trade Daily Reviewer
====================================================

HiveMind agent that analyzes daily trading performance and provides
structured insights for portfolio management decisions.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from packages.core.hivemind.base import BaseAgent

logger = logging.getLogger("cortex_analyst")


class CortexAnalyst:
    """
    HiveMind risk & performance analyst.

    Input context is expected to be a dict like:
    {
        "date": "2025-11-21",
        "pnl": {
            "day": 1200.5,
            "max_dd": -3500.0,
            "by_strategy": {
                "intraday_short_strangle": {...},
                "trend_credit_spread": {...}
            }
        },
        "trades": [...],
        "regime": {
            "NIFTY": {"regime": "LOW_MEAN_REVERT", "iv_rank": 32.1}
        },
        "execution": {
            "limit_chase": {
                "total_saves_rs": 780.0,
                "timeouts": 2,
                "slippage_stops": 1
            }
        },
        "filters": {
            "options_ranker": {
                "setups_evaluated": 14,
                "rejections": {
                    "WEAK_TREND": 5,
                    "LIQUIDITY": 3,
                    "RISK_CAP": 2
                }
            }
        }
    }
    """

    def __init__(self, vector_store=None, llm_client=None) -> None:
        # Import here to avoid circular dependency
        from packages.core.hivemind.base import BaseAgent
        # Initialize as BaseAgent subclass
        BaseAgent.__init__(
            self,
            name="CortexAnalyst",
            role=(
                "You are the Cortex Analyst for a live systematic trading system (AITRAPP). "
                "You read performance metrics, trade logs, and regime context and output "
                "structured, concise insights that a portfolio manager can act on tomorrow."
            ),
            vector_store=vector_store,
            llm_client=llm_client,
        )

    def _construct_prompt(self, context: Dict[str, Any]) -> str:
        """
        Override to enforce a strict JSON schema that we can reliably consume.
        """
        # Extract core context (BaseAgent will handle RAG if present)
        core = context.get("core", context)
        
        schema_hint = {
            "summary": "1–3 sentence narrative of the day.",
            "issues": ["short bullet issues detected today"],
            "risk_flags": ["items that threaten capital if ignored"],
            "config_tweaks": [
                "very concrete small tweaks, e.g. 'raise ADX threshold for trend_credit_spread from 22 to 25'"
            ],
            "focus_areas_tomorrow": [
                "what to watch or collect more data on tomorrow"
            ],
            "confidence": 0.0,
        }

        return (
            "You are auditing today's trading session for an automated options "
            "trading system on NSE (NIFTY/BANKNIFTY).\n\n"
            "INPUT CONTEXT (JSON):\n"
            f"{json.dumps(core, indent=2)}\n\n"
            "TASK:\n"
            "1. Read the context carefully: pnl, trades, regimes, execution stats, filter rejections.\n"
            "2. Identify the key story of the day, major issues, and specific config tweaks you would suggest.\n"
            "3. Return STRICT JSON ONLY, no markdown, no commentary, matching this schema:\n"
            f"{json.dumps(schema_hint, indent=2)}\n"
            "- 'config_tweaks' MUST be small, safe, reversible suggestions (no large leverage changes).\n"
            "- 'confidence' MUST be a float between 0.0 and 1.0.\n"
        )

    def _heuristic_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Heuristic fallback for CortexAnalyst.
        """
        pnl = context.get("pnl", {})
        daily_pnl = pnl.get("day", 0.0) if isinstance(pnl, dict) else pnl
        
        issues = []
        if daily_pnl < -1000:
            issues.append("Negative daily PnL exceeds threshold")
        
        return {
            "summary": f"Daily PnL: ₹{daily_pnl:.2f}. System operational.",
            "issues": issues,
            "risk_flags": [],
            "config_tweaks": [],
            "focus_areas_tomorrow": ["Monitor regime shifts", "Review execution stats"],
            "confidence": 0.5,
        }

