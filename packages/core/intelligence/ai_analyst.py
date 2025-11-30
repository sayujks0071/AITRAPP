"""
AI Analyst - Self-Evolving Trading System
==========================================

Self-Evolving Agent that:
1. Reads Metrics
2. Consults RAG Memory
3. Generates Config Patches
4. Applies Evolution

Usage:
    from packages.core.intelligence import AIAnalyst
    from packages.core.rag_memory import RAGMemory
    
    memory = RAGMemory()
    analyst = AIAnalyst(config_path="configs/kite_day1_live.yaml", memory=memory)
    
    # At end of day
    daily_metrics = {
        "date": "2025-11-20",
        "pnl": 5000.0,
        "win_rate": 0.65,
        "regime": "HIGH_VOL",
        "top_rejection": "MARGIN_LIMIT",
        "avg_limit_chase_savings": 0.3,
        "timeouts": 8,
        "rejections": {"WEAK_TREND": 12}
    }
    analyst.perform_eod_analysis(daily_metrics)
"""

import logging
import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

from packages.core.rag_memory import RAGMemory, TradingEpisode

# Try to import OpenAI (optional)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

logger = logging.getLogger("cortex")


class AIAnalyst:
    """
    Self-Evolving Agent.
    
    1. Reads Metrics.
    2. Consults RAG Memory.
    3. Generates Config Patches.
    4. Applies Evolution.
    """
    
    def __init__(self, config_path: str, memory: RAGMemory):
        """
        Initialize AI Analyst.
        
        Args:
            config_path: Path to YAML config file to evolve
            memory: RAG Memory instance for historical context
        """
        self.config_path = Path(config_path)
        self.memory = memory
        
        # Check for OpenAI API key
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.llm_enabled = False
        self.client = None
        
        if self.openai_api_key and OPENAI_AVAILABLE:
            try:
                self.client = OpenAI(api_key=self.openai_api_key)
                self.llm_enabled = True
                logger.info("✅ OpenAI API configured - LLM reasoning enabled")
            except Exception as e:
                logger.warning(f"Failed to configure OpenAI API: {e}")
                self.llm_enabled = False
        elif self.openai_api_key and not OPENAI_AVAILABLE:
            logger.warning("OPENAI_API_KEY found but openai not installed. Install with: pip install openai")
        else:
            logger.info("Using heuristic-based analysis (OPENAI_API_KEY not set)")
        
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
    
    def perform_eod_analysis(self, daily_metrics: Dict[str, Any]) -> None:
        """
        End-of-Day Routine: Analyze -> Evolve.
        
        This is the main entry point for daily analysis:
        1. Contextualize current day with historical episodes
        2. Generate suggestions based on metrics and history
        3. Apply config patches if needed
        4. Store episode in memory
        
        Args:
            daily_metrics: Dictionary containing daily trading metrics
                Required keys:
                    - date: str (e.g., "2025-11-20")
                    - pnl: float
                    - win_rate: float
                    - regime: str (e.g., "HIGH_VOL", "LOW_VOL")
                Optional keys:
                    - top_rejection: str
                    - avg_limit_chase_savings: float
                    - timeouts: int
                    - rejections: Dict[str, int]
        """
        logger.info("🧠 Cortex: Starting EOD Analysis...")
        
        # 1. Contextualize
        regime = daily_metrics.get("regime", "UNKNOWN")
        past_episodes = self.memory.retrieve_relevant_episodes(regime, limit=10)
        
        logger.info(
            f"📚 Retrieved {len(past_episodes)} historical episodes for regime: {regime}"
        )
        
        # 2. Heuristic Analysis (The "LLM" Logic)
        # In a real setup, you'd send `prompt` to OpenAI API here.
        suggestions = self._generate_suggestions(daily_metrics, past_episodes)
        
        if not suggestions:
            logger.info("🧠 Cortex: No evolution required today.")
            # Still store the episode even if no changes
            self._store_episode(daily_metrics, {})
            return
        
        # 3. Apply Evolution (Self-Patching)
        applied = self._apply_config_patches(suggestions)
        
        if not applied:
            logger.warning("🧠 Cortex: Failed to apply config patches")
            # Still store the episode
            self._store_episode(daily_metrics, suggestions)
            return
        
        # 4. Memorize
        self._store_episode(daily_metrics, suggestions)
        
        logger.info("✅ Cortex: EOD Analysis complete")
    
    def _generate_suggestions(
        self, 
        metrics: Dict[str, Any], 
        history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate config patch suggestions using LLM (if available) or heuristics.
        
        This is where the "intelligence" happens:
        1. If Gemini API is available: Uses LLM for advanced reasoning
        2. Otherwise: Uses heuristic rules as fallback
        
        Args:
            metrics: Current day's metrics
            history: Historical episodes from same regime
            
        Returns:
            Dictionary of config patches (key_path -> new_value)
        """
        # Try LLM first if available
        if self.llm_enabled:
            try:
                patches = self._generate_suggestions_llm(metrics, history)
                if patches:
                    logger.info("🤖 LLM-generated suggestions")
                    return patches
            except Exception as e:
                logger.warning(f"LLM generation failed, falling back to heuristics: {e}")
        
        # Fallback to heuristic rules
        patches = {}
        
        # Logic A: Execution Tuning
        # If Limit Chase saved < 0.5 pts avg, maybe market is too fast?
        avg_savings = metrics.get("avg_limit_chase_savings", 0)
        timeouts = metrics.get("timeouts", 0)
        
        if avg_savings < 0.5 and timeouts > 5:
            logger.info("💡 Insight: Limit Chase struggling. Suggesting wider slippage.")
            patches['execution.limit_chase.max_slippage_abs'] = 7.0  # Evolve from 5.0
        
        # Logic B: Strategy Tuning (Trend)
        # If too many 'WEAK_TREND' rejections but market moved? Lower ADX.
        rejections = metrics.get("rejections", {})
        weak_trend_rejections = rejections.get("WEAK_TREND", 0)
        
        if weak_trend_rejections > 10:
            # Check history: Did we lose money on low ADX days?
            losses_on_low_adx = any(
                e.get('pnl', 0) < 0 for e in history 
                if e.get('config_snapshot', {}).get('strategies.trend_credit_spread.adx_threshold', 22) < 22
            )
            
            if not losses_on_low_adx:
                logger.info("💡 Insight: Trend filter too strict. Relaxing ADX.")
                patches['strategies.trend_credit_spread.adx_threshold'] = 20.0  # Evolve from 22.0
        
        # Logic C: Risk Tuning
        # If margin limit hit frequently, maybe reduce position sizing
        margin_rejections = rejections.get("MARGIN_LIMIT", 0)
        if margin_rejections > 5:
            # Check if we're consistently hitting margin limits
            recent_margin_issues = sum(
                1 for e in history[:5] 
                if e.get('primary_rejection_reason') == 'MARGIN_LIMIT'
            )
            
            if recent_margin_issues >= 3:
                logger.info("💡 Insight: Frequent margin limits. Suggesting lower position sizing.")
                # This would need to be adjusted based on actual config structure
                patches['risk.per_trade_risk_pct'] = 0.20  # Reduce from 0.25
        
        # Logic D: Win Rate Based Tuning
        # If win rate is low but PnL is positive, maybe increase position size
        win_rate = metrics.get("win_rate", 0)
        pnl = metrics.get("pnl", 0)
        
        if win_rate < 0.5 and pnl > 0:
            # Check if this pattern is consistent in history
            similar_episodes = [
                e for e in history 
                if e.get('win_rate', 0) < 0.5 and e.get('pnl', 0) > 0
            ]
            
            if len(similar_episodes) >= 2:
                logger.info("💡 Insight: Low win rate but profitable. Consider increasing size.")
                # This is a more conservative suggestion - just log for now
                logger.info("   (Suggestion logged, not auto-applied for safety)")
        
        return patches
    
    def _generate_suggestions_llm(
        self,
        metrics: Dict[str, Any],
        history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate suggestions using OpenAI LLM.
        
        Args:
            metrics: Current day's metrics
            history: Historical episodes from same regime
            
        Returns:
            Dictionary of config patches (key_path -> new_value)
        """
        if not OPENAI_AVAILABLE or not self.client:
            return {}
        
        try:
            # Build prompt
            prompt = self._build_llm_prompt(metrics, history)
            
            # Call OpenAI GPT-4o
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert algorithmic trading system analyst. Analyze trading performance and suggest config parameter adjustments. Respond with JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            result_text = response.choices[0].message.content
            
            # Parse response
            patches = self._parse_llm_response(result_text, metrics)
            
            return patches
            
        except Exception as e:
            logger.error(f"LLM generation error: {e}", exc_info=True)
            return {}
    
    def _build_llm_prompt(
        self,
        metrics: Dict[str, Any],
        history: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for LLM"""
        regime = metrics.get("regime", "UNKNOWN")
        rejections = metrics.get("rejections", {})
        win_rate = metrics.get("win_rate", 0.0)
        pnl = metrics.get("pnl", 0.0)
        
        prompt = f"""You are an expert algorithmic trading system analyst. Analyze today's trading performance and suggest config parameter adjustments.

Today's Metrics:
- Regime: {regime}
- PnL: ₹{pnl:.2f}
- Win Rate: {win_rate:.1%}
- Entries: {metrics.get('entries', 0)}
- Top Rejection: {metrics.get('top_rejection', 'NONE')}
- Rejections: {dict(list(rejections.items())[:5])}

Historical Context (similar regime):
"""
        
        if history:
            for i, ep in enumerate(history[:3], 1):
                prompt += f"""
Episode {i} ({ep.get('date', 'N/A')}):
- PnL: ₹{ep.get('pnl', 0):.2f}
- Win Rate: {ep.get('win_rate', 0):.1%}
- Rejection: {ep.get('primary_rejection_reason', 'NONE')}
- Config Changes: {ep.get('config_snapshot', {})}
"""
        else:
            prompt += "\nNo similar historical episodes found.\n"
        
        prompt += """
Task: Analyze the metrics and suggest specific YAML config parameter changes.

Output format (JSON only, no explanation):
{
  "config_patches": {
    "path.to.parameter": new_value,
    ...
  },
  "reasoning": "brief explanation"
}

If no changes needed, return: {"config_patches": {}, "reasoning": "no changes needed"}

Focus on:
1. If too many rejections of a specific type → adjust related filters
2. If win rate is low → tighten filters or reduce position sizes
3. If margin limits hit frequently → reduce position sizing
4. If slippage is high → adjust execution parameters

Return only valid JSON:"""

        return prompt
    
    def _parse_llm_response(self, response_text: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM response into config patches"""
        import json
        import re
        
        try:
            # Try to extract JSON from response
            # Remove markdown code blocks if present
            response_text = re.sub(r'```json\n?', '', response_text)
            response_text = re.sub(r'```\n?', '', response_text)
            response_text = response_text.strip()
            
            # Parse JSON
            result = json.loads(response_text)
            
            patches = result.get("config_patches", {})
            reasoning = result.get("reasoning", "")
            
            if reasoning:
                logger.info(f"🤖 LLM Reasoning: {reasoning}")
            
            return patches
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response text: {response_text[:200]}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}", exc_info=True)
            return {}
    
    def _apply_config_patches(self, patches: Dict[str, Any]) -> bool:
        """
        Safe Config Patching.
        
        Reads YAML -> Updates Keys -> Writes YAML.
        Uses nested key path syntax (e.g., "strategies.trend_credit_spread.adx_threshold")
        
        Args:
            patches: Dictionary of key_path -> new_value mappings
            
        Returns:
            True if patches were applied successfully, False otherwise
        """
        if not self.config_path.exists():
            logger.error(f"❌ Config file not found: {self.config_path}")
            return False
        
        try:
            # Read current config
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            
            updated = False
            
            for key_path, value in patches.items():
                # key_path looks like "strategies.trend_credit_spread.adx_threshold"
                keys = key_path.split('.')
                target = config
                
                # Navigate to the target dictionary
                for k in keys[:-1]:
                    if k not in target:
                        target[k] = {}
                    target = target[k]
                
                # Get old value for logging
                old_val = target.get(keys[-1])
                
                # Update value
                if old_val != value:
                    target[keys[-1]] = value
                    logger.info(
                        f"🧬 Evolving: {key_path} {old_val} -> {value}"
                    )
                    updated = True
                else:
                    logger.debug(
                        f"⏭️  Skipping: {key_path} already set to {value}"
                    )
            
            if updated:
                # Write back to file
                with open(self.config_path, 'w') as f:
                    yaml.dump(config, f, sort_keys=False, default_flow_style=False)
                logger.info(f"✅ Evolution Applied to Config: {self.config_path}")
                return True
            else:
                logger.info("ℹ️  No changes needed (values already set)")
                return True  # Still success, just no changes
            
        except Exception as e:
            logger.error(f"❌ Evolution Failed: {e}", exc_info=True)
            return False
    
    def _store_episode(
        self, 
        daily_metrics: Dict[str, Any], 
        applied_patches: Dict[str, Any]
    ) -> None:
        """
        Store trading episode in RAG Memory.
        
        Args:
            daily_metrics: Daily metrics dictionary
            applied_patches: Config patches that were applied (or attempted)
        """
        try:
            episode = TradingEpisode(
                date=daily_metrics.get('date', ''),
                pnl=daily_metrics.get('pnl', 0.0),
                win_rate=daily_metrics.get('win_rate', 0.0),
                dominant_regime=daily_metrics.get('regime', 'UNKNOWN'),
                primary_rejection_reason=daily_metrics.get('top_rejection', 'NONE'),
                config_snapshot=applied_patches  # Store what we changed
            )
            
            self.memory.add_episode(episode)
            logger.info(f"💾 Episode stored: {episode.date}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store episode: {e}", exc_info=True)
    
    def get_evolution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent evolution history (episodes with config changes).
        
        Args:
            limit: Maximum number of episodes to return
            
        Returns:
            List of episodes that had config patches applied
        """
        all_episodes = self.memory.get_all_episodes(limit=limit * 2)
        
        # Filter to episodes with config changes
        evolved_episodes = [
            e for e in all_episodes 
            if e.get('config_snapshot', {})
        ]
        
        return evolved_episodes[:limit]

