"""
SG-1 Strategy Generator - Level 6 Self-Replicating System
==========================================================

This module contains two classes:
1. SG1Generator - Generates new trading strategy code files (Level 6)
2. SG1StrategyGenerator - HiveMind agent for config tuning suggestions
"""

from __future__ import annotations

import os
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Literal, Optional

# Try import openai
try:
    from openai import OpenAI
    HAS_LLM = True
except ImportError:
    HAS_LLM = False
    OpenAI = None

from packages.core.rag_memory import RAGMemory
from packages.core.validation.safety import CodeSafetyInspector

# BaseAgent will be imported lazily in __init__ to avoid circular import

logger = logging.getLogger("sg1")

Priority = Literal["LOW", "MEDIUM", "HIGH"]


# ============================================================================
# OLD SG1Generator - Generates new strategy code files (Level 6)
# ============================================================================

class SG1Generator:
    """
    SG-1: Autonomous Strategy Generator (Level 6).
    
    Uses LLM to write new trading algorithms based on RAG context.
    This is the original SG-1 that generates new strategy code files.
    """
    
    def __init__(self, memory: RAGMemory):
        """
        Initialize SG-1 Generator.
        
        Args:
            memory: RAG Memory instance
        """
        self.memory = memory
        self.safety = CodeSafetyInspector()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        self.model_name = "gpt-4o"  # Default model for code generation
        
        if HAS_LLM and self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("✅ SG-1: OpenAI configured - Strategy generation enabled")
            except Exception as e:
                logger.error(f"SG-1: Failed to configure OpenAI: {e}")
                self.client = None
        else:
            logger.error("SG-1 requires OPENAI_API_KEY and openai package.")
            self.client = None
    
    @property
    def model(self):
        """Backward compatibility property."""
        return self.client
    
    def generate_new_strategy(self, regime_focus: str = None) -> Optional[str]:
        """
        Generate a new trading strategy for the specified regime.
        
        Args:
            regime_focus: Target market regime (e.g., "SIDEWAYS_CHOP", "LOW_VOL")
                         If None, generates a general strategy.
        
        Returns:
            Path to generated strategy file, or None if generation failed
        """
        if not self.client:
            return None
        
        logger.info(f"🤖 SG-1: Initiating Strategy Generation Protocol. Focus: {regime_focus or 'General'}")
        
        # 1. Retrieve Context (What works? What fails?)
        context = "Focus on a MEAN REVERSION strategy for CHOPPY/SIDEWAYS regimes."
        if regime_focus:
            context = f"Focus on a strategy specifically for {regime_focus} regimes."
        
        # 2. Build Prompt
        prompt = f"""
You are an elite Quantitative Architect for an options trading system on NSE (NIFTY/BANKNIFTY).

TASK: Write a COMPLETE, RUNNABLE Python file for a new trading strategy.

REQUIREMENTS:
- Class must inherit from `packages.core.strategies.base.Strategy`
- Implement `generate_signals(self, context: StrategyContext) -> List[Signal]`
- Implement `validate(self, context: StrategyContext) -> bool`
- Use safe imports only (pandas, numpy, datetime, typing)
- NO system calls, file I/O, or network operations
- Include proper error handling

CONTEXT: {context}

Return ONLY the Python code. No markdown, no explanations, no code fences.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert Python developer for algorithmic trading systems. Write complete, runnable code only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
            )
            
            code = self._clean_response(response.choices[0].message.content)
            
            # 3. Validate Code
            if not self.safety.validate_code(code):
                logger.error("❌ SG-1: Generated code failed safety validation")
                return None
            
            # 4. Save to generated/ folder
            regime_safe = re.sub(r'[^a-z0-9_]', '_', (regime_focus or "general").lower())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"sg1_{regime_safe}_{timestamp}.py"
            
            generated_dir = Path("packages/core/strategies/generated")
            generated_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = generated_dir / filename
            with open(filepath, 'w') as f:
                f.write(code)
            
            logger.info(f"✅ SG-1: Strategy deployed to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"SG-1 Generation Failed: {e}", exc_info=True)
            return None
    
    def _clean_response(self, text: str) -> str:
        """Remove markdown code fences and extra formatting."""
        # Remove ```python and ``` markers
        text = re.sub(r'```python\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        return text.strip()


# ============================================================================
# NEW SG1StrategyGenerator - HiveMind Config Tuning Agent
# ============================================================================

class SG1StrategyGenerator:
    """
    SG-1: Strategy & Config Generator / Tuner (HiveMind Agent).

    Input context (suggested):
    {
        "date": "2025-11-21",
        "strategies": {
            "intraday_short_strangle": {
                "trades": {...},
                "win_rate": 0.55,
                "avg_rr": 1.4,
                "streak": -2,
                "config": {...}
            },
            "trend_credit_spread": {
                "trades": {...},
                "win_rate": 0.40,
                "avg_rr": 0.8,
                "streak": -4,
                "config": {...}
            }
        },
        "regimes": {...},
        "execution": {...}
    }

    SG-1 should propose very small, local config changes, not radical rewrites.
    """

    def __init__(self, vector_store=None, llm_client=None) -> None:
        # Import here to avoid circular dependency
        from packages.core.hivemind.base import BaseAgent
        # Initialize as BaseAgent subclass
        BaseAgent.__init__(
            self,
            name="SG1StrategyGenerator",
            role=(
                "You are SG-1, a cautious strategy configuration generator. "
                "You examine performance and propose very small, reversible config tweaks "
                "for tomorrow (like nudging thresholds, tightening filters, or reducing size)."
            ),
            vector_store=vector_store,
            llm_client=llm_client,
        )

    def _construct_prompt(self, context: Dict[str, Any]) -> str:
        # Extract core context (BaseAgent will handle RAG if present)
        core = context.get("core", context)
        
        schema_hint = {
            "summary": "short description of what you want to change and why",
            "proposed_changes": [
                {
                    "path": "strategies.intraday_short_strangle.adx_threshold",
                    "old_value": 22.0,
                    "new_value": 25.0,
                    "reason": "short explanation tied to observed stats",
                    "priority": "HIGH",
                }
            ],
            "changes_safe_to_apply_automatically": False,
            "notes": [
                "optional caveats or 'need more data' comments"
            ],
        }

        return (
            "You are tuning a live options trading system (NSE index options). "
            "Your job is to suggest SMALL, LOCAL config changes for tomorrow, based on the stats.\n\n"
            "IMPORTANT GUARDRAILS:\n"
            "- DO NOT suggest leverage increases.\n"
            "- DO NOT suggest removing risk limits or stop losses.\n"
            "- Prefer: nudging thresholds (e.g. ADX, IV rank bands), reducing max positions, or tightening filters.\n"
            "- All changes must be safe and reversible.\n\n"
            "INPUT CONTEXT (JSON):\n"
            f"{json.dumps(core, indent=2)}\n\n"
            "TASK:\n"
            "1. Inspect each strategy's performance (win_rate, streak, RR, etc.).\n"
            "2. Identify at most 3 small config changes that could improve robustness.\n"
            "3. Return STRICT JSON ONLY with this schema:\n"
            f"{json.dumps(schema_hint, indent=2)}\n"
            "- 'path' is a dot-path into the YAML/JSON config.\n"
            "- 'priority' must be one of: 'LOW', 'MEDIUM', 'HIGH'.\n"
            "- 'changes_safe_to_apply_automatically' is true only if all changes are extremely conservative.\n"
        )

    def _heuristic_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Heuristic fallback for SG1StrategyGenerator.
        """
        strategies = context.get("strategies", {})
        changes = []
        
        for strat_name, strat_data in strategies.items():
            win_rate = strat_data.get("win_rate", 0.5)
            streak = strat_data.get("streak", 0)
            
            # Simple heuristic: if win rate is low and streak is negative, suggest tightening
            if win_rate < 0.45 and streak < -3:
                changes.append({
                    "path": f"strategies.{strat_name}.max_portfolio_heat",
                    "old_value": 0.3,
                    "new_value": 0.25,
                    "reason": f"Reducing size due to low win rate ({win_rate:.1%}) and negative streak ({streak})",
                    "priority": "MEDIUM"
                })
        
        return {
            "summary": "Heuristic analysis suggests conservative sizing adjustments.",
            "proposed_changes": changes[:3],  # Max 3 changes
            "changes_safe_to_apply_automatically": len(changes) == 0,
            "notes": ["Heuristic fallback - LLM unavailable for detailed analysis"]
        }
