"""
Strategic Memory Engine (SME) - Level 8
=======================================

Level 8 Intelligence: Long-Term Strategic Memory.

Tracks:
1. Lineage: How/Why strategies evolved (V1 -> V2).
2. Regime Fit: Which strategy dominates which market state.
3. Seasonality: Time-based edge analysis.
"""

import json
import os
import logging
import datetime as dt
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

logger = logging.getLogger("sme")


class StrategicMemoryEngine:
    """
    Level 8 Intelligence: Long-Term Strategic Memory.
    
    Tracks:
    1. Lineage: How/Why strategies evolved (V1 -> V2).
    2. Regime Fit: Which strategy dominates which market state.
    3. Seasonality: Time-based edge analysis.
    """
    
    def __init__(self, data_dir: str = "data/sme"):
        """
        Initialize the Strategic Memory Engine.
        
        Args:
            data_dir: Directory to store SME data files
        """
        self.data_dir = data_dir
        self.lineage_file = os.path.join(data_dir, "lineage.json")
        self.matrix_file = os.path.join(data_dir, "performance_matrix.json")
        self._ensure_db()
    
    def _ensure_db(self):
        """Ensure database files and directory exist"""
        os.makedirs(self.data_dir, exist_ok=True)
        for fpath in [self.lineage_file, self.matrix_file]:
            if not os.path.exists(fpath):
                with open(fpath, 'w') as f:
                    json.dump({}, f)
    
    # --- 1. STRATEGY LINEAGE (The "Ancestry.com" of Algo) ---
    
    def register_evolution(
        self,
        parent: str,
        child: str,
        reason: str,
        config_diff: Dict
    ):
        """
        Records when SG-1 or Cortex creates a new version.
        
        Args:
            parent: Parent strategy name
            child: New strategy name (evolved from parent)
            reason: Reason for evolution
            config_diff: Configuration differences between parent and child
        """
        tree = self._load(self.lineage_file)
        
        entry = {
            "timestamp": dt.datetime.now().isoformat(),
            "parent": parent,
            "child": child,
            "reason": reason,
            "diff": config_diff
        }
        
        # Add child node
        tree[child] = entry
        
        # Update parent's children list
        if parent in tree:
            if "children" not in tree[parent]:
                tree[parent]["children"] = []
            tree[parent]["children"].append(child)
        
        self._save(self.lineage_file, tree)
        logger.info(f"🧬 SME: Registered Evolution {parent} -> {child} ({reason})")
    
    def get_lineage_story(self, strategy_name: str) -> List[Dict]:
        """
        Trace back why a strategy exists.
        
        Args:
            strategy_name: Name of the strategy to trace
            
        Returns:
            List of lineage entries from oldest to newest
        """
        tree = self._load(self.lineage_file)
        story = []
        curr = strategy_name
        
        while curr and curr in tree:
            node = tree[curr]
            story.append(node)
            curr = node.get("parent")
        
        return story[::-1]  # Oldest to newest
    
    # --- 2. REGIME PERFORMANCE MATRIX (The "Playbook") ---
    
    def update_performance(
        self,
        date: str,
        regime: str,
        strategy_metrics: Dict[str, Any]
    ):
        """
        Ingests daily results to build the Regime/Strategy heatmap.
        
        Args:
            date: Date string (ISO format)
            regime: Market regime (e.g., "HIGH_VOL", "LOW_MEAN_REVERT")
            strategy_metrics: Dictionary of strategy performance metrics
                Example: {'TrendCreditSpreadV1': {'pnl': 500, 'win': 1, 'loss': 0, 'entries': 2}}
        """
        matrix = self._load(self.matrix_file)
        
        # Structure: matrix[Regime][Strategy] = {accumulated stats}
        if regime not in matrix:
            matrix[regime] = {}
        
        for strat, stats in strategy_metrics.items():
            if strat not in matrix[regime]:
                matrix[regime][strat] = {
                    "pnl": 0.0,
                    "trades": 0,
                    "wins": 0,
                    "days": 0
                }
            
            rec = matrix[regime][strat]
            rec["pnl"] += stats.get("pnl", 0)
            rec["trades"] += stats.get("entries", 0)
            # Handle both "wins" (plural) and "win" (singular) for compatibility
            wins = stats.get("wins", stats.get("win", 0))
            rec["wins"] += wins
            rec["days"] += 1
        
        self._save(self.matrix_file, matrix)
        logger.debug(f"✅ SME: Updated performance for {len(strategy_metrics)} strategies in {regime}")
    
    def query_best_strategies(self, current_regime: str) -> List[Tuple[str, float]]:
        """
        Returns list of (Strategy, WinRate) sorted by performance in this regime.
        
        Args:
            current_regime: Market regime to query
            
        Returns:
            List of (strategy_name, win_rate) tuples, sorted by win rate (descending)
        """
        matrix = self._load(self.matrix_file)
        if current_regime not in matrix:
            return []
        
        candidates = []
        for strat, stats in matrix[current_regime].items():
            if stats["trades"] < 5:
                continue  # Ignore unproven
            win_rate = stats["wins"] / stats["trades"]
            candidates.append((strat, win_rate))
        
        return sorted(candidates, key=lambda x: x[1], reverse=True)
    
    # --- 3. SEASONAL LEARNING (The "Calendar") ---
    
    def analyze_seasonality(self) -> Dict[str, str]:
        """
        Simple heuristic analysis of time-based edges.
        (In production, this would query a TimeSeries DB).
        
        Returns:
            Dictionary mapping day names to regime/behavior patterns
        """
        # Mock logic for demonstration:
        # Returns insights like "Friday: Low Volatility", "Monday: Trend Day"
        return {
            "Monday": "BULL_BIAS",
            "Friday": "THETA_DECAY"
        }
    
    # --- HELPERS ---
    
    def _load(self, fpath: str) -> Dict:
        """Load JSON data from file"""
        try:
            with open(fpath, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _save(self, fpath: str, data: Dict):
        """Save JSON data to file"""
        with open(fpath, 'w') as f:
            json.dump(data, f, indent=2)
