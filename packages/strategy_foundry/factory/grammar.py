"""Strategy Grammar for Foundry"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import hashlib
import json

@dataclass
class StrategyRule:
    type: str
    params: Dict[str, Any]

@dataclass
class StrategyConfig:
    entry_rules: List[StrategyRule]
    exit_rules: List[StrategyRule]
    filters: List[StrategyRule]

    def get_id(self) -> str:
        """Stable hash of the strategy configuration"""
        data = {
            "entry": [r.__dict__ for r in self.entry_rules],
            "exit": [r.__dict__ for r in self.exit_rules],
            "filters": [r.__dict__ for r in self.filters]
        }
        s = json.dumps(data, sort_keys=True)
        return hashlib.sha256(s.encode()).hexdigest()[:12]

    def to_summary(self) -> str:
        """Human readable summary"""
        entries = ", ".join([f"{r.type}({r.params})" for r in self.entry_rules])
        exits = ", ".join([f"{r.type}({r.params})" for r in self.exit_rules])
        filters = ", ".join([f"{r.type}({r.params})" for r in self.filters]) if self.filters else "None"
        return f"ENTRY: [{entries}] | EXIT: [{exits}] | FILTER: [{filters}]"

# --- Parameter Space ---

BLOCK_TYPES = {
    "ENTRY": ["BREAKOUT_ORB", "BREAKOUT_DONCHIAN", "TREND_EMA_CROSS", "MEANREV_RSI", "MEANREV_BB"],
    "EXIT": ["STOP_ATR", "STOP_TIME", "TARGET_FIXED", "EXIT_SESSION"],
    "FILTER": ["FILTER_TREND_HTF", "FILTER_VOL_ATR", "FILTER_TIME_NO_TRADE"]
}

PARAM_RANGES = {
    "BREAKOUT_ORB": {"start_time": ["09:15"], "end_time": ["09:30", "09:45", "10:15"]},
    "BREAKOUT_DONCHIAN": {"period": [10, 20, 50]},
    "TREND_EMA_CROSS": {"fast": [9, 13, 20], "slow": [21, 34, 50]},
    "MEANREV_RSI": {"period": [14], "lower": [20, 30], "upper": [70, 80]},
    "MEANREV_BB": {"period": [20], "std": [2.0]},

    "STOP_ATR": {"period": [14], "multiplier": [1.5, 2.0, 3.0]},
    "STOP_TIME": {"bars": [6, 12, 24, 72]}, # 30m, 1h, 2h, 6h (for 5m bars)
    "TARGET_FIXED": {"risk_reward": [1.5, 2.0, 3.0]},
    "EXIT_SESSION": {"time": ["15:20"]}, # Mandatory

    "FILTER_TREND_HTF": {"period": [50, 200]},
    "FILTER_VOL_ATR": {"period": [14], "min_percentile": [0, 20], "max_percentile": [80, 100]},
    "FILTER_TIME_NO_TRADE": {"start": ["09:15"], "end": ["09:45"]} # Avoid first 30m
}
