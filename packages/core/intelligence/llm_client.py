"""
LLM Client - Pluggable Backend for Claude & OpenAI
==================================================

Unified interface for multiple LLM providers.
Supports Anthropic (Claude) and OpenAI with environment-based configuration.
"""

from __future__ import annotations

import os
import json
import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

logger = logging.getLogger("hivemind.llm")

# --- OpenAI support (optional) ---
try:
    from openai import OpenAI as OpenAIClient
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    OpenAIClient = None

# --- Anthropic (Claude) support (optional) ---
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    anthropic = None


@dataclass
class LLMConfig:
    provider: str = os.getenv("HIVEMIND_PROVIDER", "anthropic").lower()
    openai_model: str = os.getenv("HIVEMIND_OPENAI_MODEL", "gpt-5")
    anthropic_model: str = os.getenv("HIVEMIND_ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    temperature: float = float(os.getenv("HIVEMIND_TEMPERATURE", "0.1"))
    max_tokens: int = int(os.getenv("HIVEMIND_MAX_TOKENS", "800"))


class LLMClient:
    """
    Thin wrapper that can talk to OpenAI or Claude (Anthropic) with one API:
        chat_json(system, user, extra_msgs=[])
    """

    def __init__(self, cfg: Optional[LLMConfig] = None):
        self.cfg = cfg or LLMConfig()
        self.provider = self.cfg.provider

        self._openai: Optional[OpenAIClient] = None
        self._anthropic: Optional[Any] = None

        # Lazy init – we don't want to fail import if a provider is unused
        self._init_provider()

    # ------------------------------------------------------------------ #
    # Provider init
    # ------------------------------------------------------------------ #
    def _init_provider(self) -> None:
        if self.provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if HAS_ANTHROPIC and api_key:
                self._anthropic = anthropic.Anthropic(api_key=api_key)
                logger.info("[LLMClient] Using Anthropic (Claude) backend.")
                return
            logger.warning("[LLMClient] Anthropic selected but not available; falling back to OpenAI.")
            self.provider = "openai"

        if self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if HAS_OPENAI and api_key:
                self._openai = OpenAIClient(api_key=api_key)
                logger.info("[LLMClient] Using OpenAI backend.")
                return
            logger.warning("[LLMClient] OpenAI selected but not available; disabling LLM.")
            self.provider = "none"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def is_available(self) -> bool:
        return self.provider in ("anthropic", "openai")

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        extra_messages: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Calls the configured LLM and returns parsed JSON.
        If anything fails, raises or returns a structured error.
        """
        if not self.is_available():
            return {"error": "llm_unavailable", "raw": None}

        messages = extra_messages[:] if extra_messages else []
        messages.insert(0, {"role": "user", "content": user_prompt})

        try:
            if self.provider == "anthropic":
                raw = self._call_anthropic(system_prompt, messages)
            else:
                raw = self._call_openai(system_prompt, messages)
        except Exception as e:
            logger.error(f"[LLMClient] LLM call failed: {e}", exc_info=True)
            return {"error": "llm_call_failed", "raw": str(e)}

        return self._parse_json(raw)

    # ------------------------------------------------------------------ #
    # Provider-specific calls
    # ------------------------------------------------------------------ #
    def _call_openai(self, system_prompt: str, messages: List[Dict[str, str]]) -> str:
        if not self._openai:
            raise RuntimeError("OpenAI client not initialized")

        resp = self._openai.chat.completions.create(
            model=self.cfg.openai_model,
            temperature=self.cfg.temperature,
            max_tokens=self.cfg.max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                *messages,
            ],
        )
        return resp.choices[0].message.content

    def _call_anthropic(self, system_prompt: str, messages: List[Dict[str, str]]) -> str:
        if not self._anthropic:
            raise RuntimeError("Anthropic client not initialized")

        # Anthropic expects a different format; we map our messages.
        # System prompt is separate; messages are user/assistant.
        api_msgs = []
        for m in messages:
            role = m.get("role", "user")
            if role not in ("user", "assistant"):
                role = "user"
            api_msgs.append({"role": role, "content": m["content"]})

        resp = self._anthropic.messages.create(
            model=self.cfg.anthropic_model,
            max_tokens=self.cfg.max_tokens,
            temperature=self.cfg.temperature,
            system=(
                system_prompt
                + "\nYou MUST respond with STRICT JSON only. No markdown, no commentary."
            ),
            messages=api_msgs,
        )

        # Anthropic returns a list of content blocks; we assume single text block.
        if not resp.content:
            return "{}"
        block = resp.content[0]
        text = getattr(block, "text", None) or getattr(block, "content", None)
        if isinstance(text, str):
            return text
        return "{}"

    # ------------------------------------------------------------------ #
    # JSON parsing
    # ------------------------------------------------------------------ #
    def _parse_json(self, text: str) -> Dict[str, Any]:
        if text is None:
            return {"error": "empty_response", "raw": None}

        try:
            return json.loads(text)
        except Exception:
            # Strip common fences
            clean = (
                text.replace("```json", "")
                .replace("```", "")
                .strip()
            )
            try:
                return json.loads(clean)
            except Exception:
                logger.warning("[LLMClient] Failed to parse JSON from LLM output.")
                return {"error": "failed_to_parse", "raw": text}




