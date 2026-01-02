from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any
import hashlib
import json

@dataclass
class StrategyBlock:
    type: str
    params: Dict[str, Any]

@dataclass
class StrategySpec:
    blocks: List[StrategyBlock]
    timeframe: str
    instrument: str
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()

    def _generate_id(self):
        # Create a stable representation for hashing (excluding id itself)
        data = {
            "blocks": [asdict(b) for b in self.blocks],
            "timeframe": self.timeframe,
            "instrument": self.instrument
        }
        s = json.dumps(data, sort_keys=True)
        return hashlib.md5(s.encode()).hexdigest()[:8]

# Parameter space definition
GRAMMAR = {
    "entry": [
        {"type": "donchian_breakout", "params": {"period": [20, 50, 100]}},
        {"type": "ema_cross", "params": {"fast": [9, 13, 21], "slow": [20, 50, 100]}},
        {"type": "rsi_long", "params": {"period": [14], "threshold": [30, 40]}}, # Mean reversion buy
        {"type": "bb_breakout", "params": {"period": [20], "std_dev": [2.0]}}
    ],
    "exit": [
        {"type": "atr_stop", "params": {"period": [14], "multiplier": [2.0, 3.0, 4.0]}},
        {"type": "time_stop", "params": {"bars": [12, 36, 72]}}, # e.g. 1h, 3h, 6h on 5m
        {"type": "profit_target", "params": {"rr": [2.0, 3.0, 5.0]}} # Risk:Reward
    ],
    "filter": [
        {"type": "adx_filter", "params": {"period": [14], "threshold": [20, 25]}},
        {"type": "ema_trend_filter", "params": {"period": [200]}}
    ]
}
