"""
Base Agent Framework - HiveMind Level 7
========================================

Abstract base class for all HiveMind agents.
Each agent has a persona and specific "Tool" capability.
Now uses pluggable LLMClient (Claude / OpenAI).
"""

from __future__ import annotations

import os
import json
import logging
from typing import Dict, Any, Optional

from packages.core.intelligence.llm_client import LLMClient, LLMConfig

logger = logging.getLogger("hivemind")


class BaseAgent:
    """
    Abstract Base Class for HiveMind Agents.
    Now uses pluggable LLMClient (Claude / OpenAI).
    """

    def __init__(
        self,
        name: str,
        role: str,
        *,
        model_name: Optional[str] = None,  # kept for compatibility; not strictly needed
        temperature: float = 0.1,
        max_tokens: int = 800,
        vector_store: Optional[Any] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.name = name
        self.role = role
        self.vector_store = vector_store

        # LLM client (defaults to env-configured backend)
        if llm_client is not None:
            self.llm = llm_client
        else:
            cfg = LLMConfig()
            # Allow overriding model via ctor if you want
            if model_name:
                if cfg.provider == "anthropic":
                    cfg.anthropic_model = model_name
                else:
                    cfg.openai_model = model_name
            # Override temperature and max_tokens if provided
            if temperature != 0.1:
                cfg.temperature = temperature
            if max_tokens != 800:
                cfg.max_tokens = max_tokens
            self.llm = LLMClient(cfg)

        # Backward compatibility properties
        self.model_name = cfg.provider  # For logging/debugging
        self.temperature = cfg.temperature
        self.max_tokens = cfg.max_tokens

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def think(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main reasoning loop.
        Optionally enriches context with RAG, then calls LLMClient.chat_json().
        """
        # Optional RAG
        if self.vector_store and "query" in context:
            try:
                rag_hits = self.vector_store.search(
                    query=context["query"],
                    top_k=context.get("rag_top_k", 6),
                    source_filter=context.get("rag_source"),
                )
                context = dict(context)
                context["rag_hits"] = rag_hits
            except Exception as e:
                logger.error(f"[{self.name}] RAG search failed: {e}", exc_info=True)

        if not self.llm.is_available():
            return self._heuristic_fallback(context)

        system_prompt = (
            f"You are {self.name}. {self.role}. "
            "You MUST respond with STRICT JSON only. No markdown, no comments."
        )
        user_prompt = self._construct_prompt(context)

        result = self.llm.chat_json(system_prompt=system_prompt, user_prompt=user_prompt)
        if "error" in result:
            # LLM error or parsing failure → heuristic fallback
            return self._heuristic_fallback(context, llm_error=result)

        return result

    # ------------------------------------------------------------------ #
    # Prompt + fallback
    # ------------------------------------------------------------------ #

    def _construct_prompt(self, context: Dict[str, Any]) -> str:
        """
        Default prompt builder. Subclasses can override for specialized schemas.
        """
        core = context.get("core", context)
        rag_hits = context.get("rag_hits", [])

        # If RAG hits exist, include them; otherwise use simple format
        if rag_hits:
            return f"""
CORE CONTEXT:
{json.dumps(core, indent=2)}

RELEVANT DOCUMENTS FROM KNOWLEDGE BASE (RAG):
{json.dumps(rag_hits, indent=2)}

TASK:
Analyze the context from your specific perspective ({self.role}).
Output your analysis as a JSON object matching the schema required for your role.
"""
        else:
            return (
                "CONTEXT DATA (JSON):\n"
                f"{json.dumps(core, indent=2)}\n\n"
                "TASK:\n"
                f"Analyze the context from your perspective as: {self.role}.\n"
                "Return a single JSON object ONLY, with keys appropriate to your role "
                "(e.g., 'analysis', 'recommendations', 'confidence', etc.)."
            )

    def _heuristic_fallback(
        self,
        context: Dict[str, Any],
        llm_error: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Simple deterministic fallback when LLM is unavailable.
        Subclasses can override to provide slightly smarter offline logic.
        """
        payload: Dict[str, Any] = {
            "status": "offline",
            "agent": self.name,
            "role": self.role,
            "insight": "LLM unavailable; using heuristic fallback.",
            "context_summary_keys": list(context.keys()),
        }
        if llm_error:
            payload["llm_error"] = llm_error
        logger.info(
            f"[{self.name}] Using heuristic fallback (LLM unavailable)."
        )
        return payload
