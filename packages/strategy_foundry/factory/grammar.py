"""Strategy grammar and components"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import hashlib
import json

@dataclass
class StrategyCandidate:
    id: str
    entry_logic: Dict[str, Any]
    exit_logic: Dict[str, Any]
    filters: List[Dict[str, Any]]
    timeframe: str
    params: Dict[str, Any] = field(default_factory=dict)

    @property
    def rule_summary(self) -> str:
        """Human-readable summary of rules"""
        entry_s = f"{self.entry_logic['type']}"
        exit_s = f"{self.exit_logic['type']}"
        filters_s = ", ".join([f['type'] for f in self.filters])
        return f"Entry: {entry_s} | Exit: {exit_s} | Filters: {filters_s} | TF: {self.timeframe}"

def generate_id(candidate: 'StrategyCandidate') -> str:
    """Stable ID hash"""
    raw = json.dumps({
        "entry": candidate.entry_logic,
        "exit": candidate.exit_logic,
        "filters": candidate.filters,
        "timeframe": candidate.timeframe,
        "params": candidate.params
    }, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()

# --- Grammar Blocks ---

ENTRY_TYPES = [
    "ORB_BREAKOUT",
    "DONCHIAN_BREAKOUT",
    "RSI_REVERSION",
    "EMA_CROSS",
    "BOLLINGER_REVERSION"
]

EXIT_TYPES = [
    "ATR_TRAIL",
    "TIME_STOP",
    "FIXED_RR"
]

FILTER_TYPES = [
    "TREND_EMA_1H",
    "VOLATILITY_ATR",
    "NO_TRADE_ZONE"
]

# Parameter definitions for randomization
PARAM_RANGES = {
    # ORB
    "orb_window_minutes": [15, 30, 60],

    # Donchian
    "donchian_period": [10, 20, 40, 60],

    # RSI
    "rsi_period": [7, 14, 21],
    "rsi_overbought": [70, 75, 80],
    "rsi_oversold": [20, 25, 30],

    # EMA
    "ema_fast": [9, 13, 20],
    "ema_slow": [21, 34, 50],

    # Bollinger
    "bb_period": [20],
    "bb_std": [2.0, 2.5],

    # Exits
    "atr_period": [14],
    "atr_multiplier": [1.5, 2.0, 3.0],
    "time_stop_bars": [6, 12, 24], # e.g. 1-2 hours on 5m
    "profit_target_rr": [1.5, 2.0, 3.0],

    # Filters
    "trend_ema_period": [50, 100, 200]
}
