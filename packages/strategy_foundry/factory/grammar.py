"""
Strategy Grammar and Parameter Space.
"""
import random
import hashlib
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

@dataclass
class StrategySpec:
    id: str
    entry_logic: Dict[str, Any]
    exit_logic: Dict[str, Any]
    filters: List[Dict[str, Any]]
    timeframe: str

    def to_json(self):
        return json.dumps(asdict(self), sort_keys=True)

    @property
    def summary(self) -> str:
        return f"{self.entry_logic['type']} + {self.exit_logic['stop_type']} stop"

class Grammar:
    def __init__(self):
        self.entry_types = ["Breakout", "TrendCross", "RSIReversion", "BollingerReversion"]
        self.stop_types = ["ATR", "FixedPct"]
        self.filter_types = ["TrendFilter", "None"]

    def generate(self, timeframe: str) -> StrategySpec:
        """Generate a random strategy specification."""
        entry = self._gen_entry()
        exit_logic = self._gen_exit()
        filters = self._gen_filters()

        # Create deterministic ID
        content = {
            "entry": entry,
            "exit": exit_logic,
            "filters": filters,
            "tf": timeframe
        }
        spec_str = json.dumps(content, sort_keys=True)
        spec_id = hashlib.md5(spec_str.encode()).hexdigest()[:12]

        return StrategySpec(
            id=spec_id,
            entry_logic=entry,
            exit_logic=exit_logic,
            filters=filters,
            timeframe=timeframe
        )

    def _gen_entry(self) -> Dict[str, Any]:
        etype = random.choice(self.entry_types)
        if etype == "Breakout":
            return {
                "type": "Breakout",
                "period": random.choice([10, 20, 50]),
                "confirm_vol": random.choice([True, False])
            }
        elif etype == "TrendCross":
            fast = random.choice([9, 20])
            slow = random.choice([20, 50, 200])
            if fast >= slow: slow = fast * 2
            return {
                "type": "TrendCross",
                "fast": fast,
                "slow": slow,
                "adx_filter": random.choice([0, 20, 25])
            }
        elif etype == "RSIReversion":
            return {
                "type": "RSIReversion",
                "period": 14,
                "buy_threshold": random.choice([20, 30, 40]),
                "sell_threshold": random.choice([60, 70, 80])
            }
        elif etype == "BollingerReversion":
            return {
                "type": "BollingerReversion",
                "period": 20,
                "std": random.choice([2.0, 2.5])
            }
        return {"type": "Unknown"}

    def _gen_exit(self) -> Dict[str, Any]:
        stype = random.choice(self.stop_types)
        sl_mult = random.choice([1.5, 2.0, 3.0])
        tp_mult = random.choice([1.5, 2.0, 3.0, 5.0])

        return {
            "stop_type": stype,
            "sl_mult": sl_mult,
            "tp_risk_reward": tp_mult,
            "time_stop_bars": random.choice([0, 12, 24, 48]) # 0 means none
        }

    def _gen_filters(self) -> List[Dict[str, Any]]:
        ftype = random.choice(self.filter_types)
        if ftype == "TrendFilter":
            return [{
                "type": "TrendFilter",
                "ema_period": random.choice([50, 200])
            }]
        return []
