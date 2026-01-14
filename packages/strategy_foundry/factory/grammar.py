from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class IndicatorParams:
    name: str
    params: Dict[str, Any]

@dataclass
class Rule:
    indicator: str  # e.g. 'rsi'
    operator: str   # '>', '<', 'cross_above', 'cross_below'
    value: Any      # 30, or another indicator reference
    params: Dict[str, Any] # params for the indicator

@dataclass
class StrategyConfig:
    strategy_id: str
    entry_rules: List[Rule]
    exit_rules: List[Rule]
    stop_loss_atr: float
    take_profit_atr: float
    max_bars_hold: int

    def to_dict(self):
        return {
            "strategy_id": self.strategy_id,
            "entry_rules": [vars(r) for r in self.entry_rules],
            "exit_rules": [vars(r) for r in self.exit_rules],
            "stop_loss_atr": self.stop_loss_atr,
            "take_profit_atr": self.take_profit_atr,
            "max_bars_hold": self.max_bars_hold
        }

