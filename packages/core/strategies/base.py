"""Base strategy interface"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from packages.core.models import Bar, Instrument, Signal, SignalSide, Tick


@dataclass
class StrategyContext:
    """
    Context passed to strategy for signal generation.
    
    Enriched with Regime and Event snapshots to prevent redundant fetching.
    
    Supports both:
    - Legacy format: Single instrument with Tick/Bar objects (for existing strategies)
    - New format: Multi-instrument dict-based data (for new strategies)
    """
    # Legacy: Single instrument context (backward compatible)
    timestamp: datetime
    instrument: Instrument
    
    # Legacy: Market data (object-based)
    latest_tick: Optional[Tick] = None
    bars_1s: List[Bar] = None
    bars_5s: List[Bar] = None
    
    # Legacy: Portfolio state (individual fields)
    net_liquid: float = 0.0
    available_margin: float = 0.0
    open_positions: int = 0
    
    # Legacy: Market regime (individual fields)
    iv_percentile: Optional[float] = None
    oi_change_pct: Optional[float] = None
    
    # NEW: Multi-instrument market data (dict-based, StatGeist-style)
    ltp: Dict[str, float] = field(default_factory=dict)  # Last traded prices by symbol
    ohlc: Dict[str, Any] = field(default_factory=dict)   # OHLC data by symbol
    
    # NEW: Account/Risk (dict-based)
    positions: List[Any] = field(default_factory=list)   # List of Position objects
    margins: Dict[str, float] = field(default_factory=dict)  # Margin data by account/segment
    
    # Patch 3: Regime and event snapshots (enriched context)
    # Supports both formats:
    # - Dict format: {"NIFTY": {"regime": "LOW_MEAN_REVERT", ...}} (current)
    # - String format: "LOW_MEAN_REVERT" (simplified, can be extracted from dict)
    regime_snapshot: Optional[Dict[str, Any]] = None  # R1 output (full dict)
    regime: Optional[str] = None  # Simplified regime string (extracted from snapshot)
    event_snapshot: Optional[Dict[str, Any]] = None  # E1 output (e.g., {"today": {"has_major_event": False, ...}})
    
    # Execution Stats
    universe_size: int = 0  # Total universe size
    token_count: int = 0     # Tokens being scanned in this cycle
    
    def __post_init__(self):
        if self.bars_1s is None:
            self.bars_1s = []
        if self.bars_5s is None:
            self.bars_5s = []
        
        # Extract simplified regime string from snapshot if available
        if self.regime_snapshot and not self.regime:
            # Try to extract regime string from snapshot
            # Format: {"NIFTY": {"regime": "LOW_MEAN_REVERT", ...}}
            for symbol, data in self.regime_snapshot.items():
                if isinstance(data, dict) and "regime" in data:
                    self.regime = data["regime"]
                    break
    
    @property
    def is_event_day(self) -> bool:
        """Helper property to check if today is an event day"""
        if self.event_snapshot:
            return self.event_snapshot.get("today", {}).get("is_event_day", False)
        return False
    
    @property
    def event_impact(self) -> str:
        """Helper property to get event impact level"""
        if self.event_snapshot:
            return self.event_snapshot.get("today", {}).get("impact", "LOW")
        return "LOW"


class Strategy(ABC):
    """
    Base class for all trading strategies.
    
    Each strategy must implement:
    - generate_signals(): Produce trading signals based on market data (sync)
    - validate(): Check if strategy can run in current conditions
    
    Optional:
    - execute(): Async execution logic (for new strategies)
    - on_tick(): Real-time tick handling (for new strategies)
    """
    
    def __init__(self, name: str, params: Dict[str, Any], priority: Optional[int] = None):
        self.name = name
        self.params = params
        
        # Patch 2: Priority (Lower = Higher Priority)
        # Can be set from params or passed directly
        if priority is not None:
            self.priority = priority
        else:
            self.priority = params.get("priority", 100)  # Default 100 if not specified
        
        self.initialized = False
        
        # Strategy state
        self.enabled = params.get("enabled", True)
        self.max_positions = params.get("max_positions", 2)
        self.current_positions = 0
        
        # Performance tracking
        self.signals_generated = 0
        self.signals_executed = 0
        self.win_count = 0
        self.loss_count = 0
        self.total_pnl = 0.0
    
    @abstractmethod
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        """
        Generate trading signals based on current market context.
        
        This is the primary method for existing strategies (sync, per-instrument).
        
        Args:
            context: Market data and state
        
        Returns:
            List of Signal objects
        """
        pass
    
    async def execute(self, context: StrategyContext) -> List[Signal]:
        """
        Async execution logic (optional, for new strategies).
        
        New strategies can implement this instead of generate_signals()
        for async/await support and multi-instrument processing.
        
        Default implementation calls generate_signals() for backward compatibility.
        
        Args:
            context: Market data and state
        
        Returns:
            List of Signal objects
        """
        # Default: delegate to sync generate_signals for backward compatibility
        return self.generate_signals(context)
    
    async def on_tick(self, tick_data: Any) -> None:
        """
        Real-time tick handling (optional, for new strategies).
        
        Called when a new tick arrives for subscribed instruments.
        Useful for high-frequency strategies that need immediate reaction.
        
        Args:
            tick_data: Tick data (format depends on market data stream)
        """
        # Default: no-op, strategies can override
        pass
    
    def validate(self, context: StrategyContext) -> bool:
        """
        Validate if strategy can run in current conditions.
        
        Args:
            context: Market data and state
        
        Returns:
            True if strategy can run, False otherwise
        """
        if not self.enabled:
            return False
        
        if self.current_positions >= self.max_positions:
            return False
        
        # Ensure we have enough data
        if not context.latest_tick:
            return False
        
        return True
    
    def on_position_opened(self) -> None:
        """Callback when a position is opened from this strategy"""
        self.current_positions += 1
        self.signals_executed += 1
    
    def on_position_closed(self, pnl: float) -> None:
        """Callback when a position is closed from this strategy"""
        self.current_positions = max(0, self.current_positions - 1)
        self.total_pnl += pnl
        
        if pnl > 0:
            self.win_count += 1
        else:
            self.loss_count += 1
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate"""
        total_trades = self.win_count + self.loss_count
        if total_trades > 0:
            return (self.win_count / total_trades) * 100
        return 0.0
    
    @property
    def sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio (placeholder - needs proper implementation)"""
        # In production, track returns series and compute properly
        return 0.0
    
    def get_param(self, key: str, default: Any = None) -> Any:
        """Get strategy parameter with default"""
        return self.params.get(key, default)
    
    def __repr__(self) -> str:
        return (
            f"{self.name}(enabled={self.enabled}, "
            f"positions={self.current_positions}/{self.max_positions}, "
            f"win_rate={self.win_rate:.1f}%)"
        )
