"""
RAG Memory System for Trading Episodes
======================================

Lite-RAG (Retrieval Augmented Generation) for Trading Context.
Stores past trading days to help the AI Analyst make informed decisions.

Usage:
    from packages.core.rag_memory import RAGMemory, TradingEpisode
    
    memory = RAGMemory()
    
    # Add a trading episode
    episode = TradingEpisode(
        date="2025-11-20",
        pnl=5000.0,
        win_rate=0.65,
        dominant_regime="HIGH_VOL",
        primary_rejection_reason="MARGIN_LIMIT",
        config_snapshot={"max_capital_pct": 0.25}
    )
    memory.add_episode(episode)
    
    # Retrieve relevant episodes
    relevant = memory.retrieve_relevant_episodes("HIGH_VOL", limit=5)
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TradingEpisode:
    """Represents a single trading day/episode"""
    date: str
    pnl: float
    win_rate: float
    dominant_regime: str
    primary_rejection_reason: str
    config_snapshot: Dict[str, Any]


class RAGMemory:
    """
    Lite-RAG (Retrieval Augmented Generation) for Trading Context.
    
    Stores past trading days to help the AI Analyst make informed decisions.
    This is the 'Retrieval' component in RAG - it stores and retrieves
    relevant past episodes based on current market regime.
    """
    
    def __init__(self, db_path: str = "data/memory.json"):
        """
        Initialize RAG Memory system.
        
        Args:
            db_path: Path to JSON file storing trading episodes
        """
        self.db_path = Path(db_path)
        self._ensure_db()
    
    def _ensure_db(self) -> None:
        """Ensure the database file and directory exist"""
        # Create directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create empty JSON array if file doesn't exist
        if not self.db_path.exists():
            with open(self.db_path, "w") as f:
                json.dump([], f, indent=2)
    
    def add_episode(self, episode: TradingEpisode) -> None:
        """
        Add a new trading episode to memory.
        
        Args:
            episode: TradingEpisode dataclass instance
        """
        data = self._load()
        
        # Convert dataclass to dict
        record = episode.__dict__
        
        # Add timestamp if not present
        if "added_at" not in record:
            record["added_at"] = datetime.now().isoformat()
        
        data.append(record)
        
        # Keep last 365 days (rolling window)
        if len(data) > 365:
            data.pop(0)
        
        self._save(data)
    
    def retrieve_relevant_episodes(
        self, 
        current_regime: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieves past days that match the current market regime.
        
        This is the 'Retrieval' in RAG - it finds similar past episodes
        to provide context for decision-making.
        
        Args:
            current_regime: Current market regime (e.g., "HIGH_VOL", "LOW_VOL")
            limit: Maximum number of episodes to return
            
        Returns:
            List of episode dictionaries, sorted by recency (most recent first)
        """
        data = self._load()
        
        # Filter by regime similarity
        relevant = [
            d for d in data 
            if d.get('dominant_regime') == current_regime
        ]
        
        # Sort by recency (most recent first)
        return sorted(
            relevant, 
            key=lambda x: x.get('date', ''), 
            reverse=True
        )[:limit]
    
    def get_all_episodes(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get all episodes, optionally limited.
        
        Args:
            limit: Maximum number of episodes to return (None = all)
            
        Returns:
            List of all episode dictionaries, sorted by recency
        """
        data = self._load()
        
        # Sort by recency
        sorted_data = sorted(
            data,
            key=lambda x: x.get('date', ''),
            reverse=True
        )
        
        if limit:
            return sorted_data[:limit]
        return sorted_data
    
    def get_episode_by_date(self, date: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific episode by date.
        
        Args:
            date: Date string (e.g., "2025-11-20")
            
        Returns:
            Episode dictionary or None if not found
        """
        data = self._load()
        
        for episode in data:
            if episode.get('date') == date:
                return episode
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get aggregate statistics from all episodes.
        
        Returns:
            Dictionary with statistics (total_episodes, avg_pnl, etc.)
        """
        data = self._load()
        
        if not data:
            return {
                "total_episodes": 0,
                "avg_pnl": 0.0,
                "avg_win_rate": 0.0,
                "regime_distribution": {}
            }
        
        total_pnl = sum(d.get('pnl', 0.0) for d in data)
        total_win_rate = sum(d.get('win_rate', 0.0) for d in data)
        
        # Count regime distribution
        regime_counts: Dict[str, int] = {}
        for d in data:
            regime = d.get('dominant_regime', 'UNKNOWN')
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        return {
            "total_episodes": len(data),
            "avg_pnl": total_pnl / len(data) if data else 0.0,
            "avg_win_rate": total_win_rate / len(data) if data else 0.0,
            "regime_distribution": regime_counts,
            "total_pnl": total_pnl
        }
    
    def _load(self) -> List[Dict[str, Any]]:
        """Load episodes from JSON file"""
        try:
            with open(self.db_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # If file is corrupted or missing, return empty list
            return []
    
    def _save(self, data: List[Dict[str, Any]]) -> None:
        """Save episodes to JSON file"""
        with open(self.db_path, "w") as f:
            json.dump(data, f, indent=2)

