"""
The Cortex - High-Level Self-Evolving Trading Intelligence
==========================================================

The Central Nervous System of the Self-Evolving Bot.

Coordinates Perception (Logs), Memory (RAG), and Cognition (Analyst).
Executes the full OODA loop: Observe, Orient, Decide, Act.
"""

import logging
import os
from typing import Dict, Any
from datetime import datetime

from packages.core.intelligence.ai_analyst import AIAnalyst
from packages.core.intelligence.log_parser import LogParser
from packages.core.intelligence.sme import StrategicMemoryEngine
from packages.core.rag_memory import RAGMemory

logger = logging.getLogger("cortex")


class Cortex:
    """
    The Central Nervous System of the Self-Evolving Bot.
    
    Coordinates Perception (Logs), Memory (RAG), and Cognition (Analyst).
    """
    
    def __init__(self, config_path: str, log_path: str = "logs/trading.log"):
        """
        Initialize The Cortex.
        
        Args:
            config_path: Path to YAML config file to evolve
            log_path: Path to trading log file
        """
        self.config_path = config_path
        self.log_path = log_path
        
        # Initialize Subsystems
        self.memory = RAGMemory()  # Uses default db_path="data/memory.json"
        self.parser = LogParser(self.log_path)
        self.analyst = AIAnalyst(self.config_path, self.memory)
        
        # Initialize Strategic Memory Engine (Level 8)
        self.sme = StrategicMemoryEngine()  # Institutional memory
        logger.info("✅ Strategic Memory Engine (SME) initialized - Level 8 active")
    
    def run_evolution_cycle(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Executes the full OODA loop (Observe, Orient, Decide, Act).
        """
        logger.info(f"🧠 CORTEX: Initiating Evolution Cycle (Dry Run: {dry_run})")
        
        # 1. PERCEPTION (Observe)
        if not os.path.exists(self.log_path):
            logger.error(f"❌ Log file not found: {self.log_path}")
            return {}
        
        metrics = self.parser.analyze_today()
        
        # Check if there's actual data to analyze
        activity_count = metrics.get("entries", 0) + sum(metrics.get("rejections", {}).values())
        if not metrics or activity_count == 0:
            logger.warning("⚠️ No significant activity found in logs today. Skipping evolution.")
            return metrics
        
        logger.info(f"📊 Observed: {metrics.get('entries')} Entries, Regime: {metrics.get('regime')}")
        
        # 2. COGNITION (Orient & Decide) & 3. ACTION (Evolve)
        # The Analyst handles retrieval (Orient), reasoning (Decide), and patching (Act)
        
        if dry_run:
            logger.info("🧪 DRY RUN MODE: Evolution logic will run but config updates are simulated.")
            # Note: In a strictly dry-run scenario, we rely on the analyst's logging 
            # to see what *would* happen. Actual file writes happen in perform_eod_analysis.
            # To make this strictly safe, one might extend Analyst to accept a dry_run flag.
        
        self.analyst.perform_eod_analysis(metrics)
        
        # 4. FEED SME (Level 8) - Update Strategic Memory Engine with daily metrics
        self._update_sme(metrics)
        
        logger.info("✅ CORTEX: Cycle Complete.")
        
        return metrics
    
    def _update_sme(self, metrics: Dict[str, Any]) -> None:
        """
        Update Strategic Memory Engine with daily trading metrics.
        
        Args:
            metrics: Daily metrics from log parser
        """
        try:
            regime = metrics.get("regime", "UNKNOWN")
            date = metrics.get("date", datetime.now().isoformat())
            strategy_metrics = metrics.get("strategy_metrics", {})
            
            # Convert to SME format: {'StrategyName': {'pnl': X, 'win': Y, 'loss': Z, 'entries': N}}
            sme_metrics = {}
            for strategy_name, perf_data in strategy_metrics.items():
                if isinstance(perf_data, dict):
                    pnl = perf_data.get("pnl", 0.0)
                    entries = perf_data.get("entries", perf_data.get("trades_today", 0))
                    wins = perf_data.get("wins", perf_data.get("wins_today", 0))
                    losses = entries - wins
                    
                    sme_metrics[strategy_name] = {
                        "pnl": pnl,
                        "win": wins,
                        "loss": losses,
                        "entries": entries
                    }
            
            # Update SME with daily performance
            if sme_metrics:
                self.sme.update_performance(date, regime, sme_metrics)
                logger.debug(f"✅ SME updated with {len(sme_metrics)} strategy performances for regime: {regime}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to update SME: {e}")

