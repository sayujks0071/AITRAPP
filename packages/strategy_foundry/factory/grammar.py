"""
Strategy Grammar and Parameter Space.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import random
import hashlib
import json

@dataclass
class StrategyConfig:
    id: str
    entry_rules: List[Dict[str, Any]]
    exit_rules: List[Dict[str, Any]]
    filters: List[Dict[str, Any]]
    params: Dict[str, Any]
    timeframe: str

    def to_json(self):
        return json.dumps(self.__dict__, sort_keys=True)

    @staticmethod
    def from_json(json_str):
        data = json.loads(json_str)
        return StrategyConfig(**data)

class Grammar:
    ENTRY_TYPES = ["trend_ema_cross", "breakout_donchian", "mean_reversion_rsi"]
    EXIT_TYPES = ["atr_stop", "time_stop", "fixed_rr"]
    FILTERS = ["ema_trend_filter", "time_filter"]

    @staticmethod
    def generate_random(timeframe: str) -> StrategyConfig:
        entry_type = random.choice(Grammar.ENTRY_TYPES)
        exit_type = random.choice(Grammar.EXIT_TYPES)
        # Always include time filter for intraday
        filters = [{"type": "time_filter", "params": {"start": "09:30", "end": "15:00"}}]

        # Randomly add trend filter
        if random.random() > 0.5:
            filters.append({"type": "ema_trend_filter", "params": {"period": random.choice([50, 100, 200])}})

        entry_rule = {"type": entry_type, "params": {}}
        exit_rule = {"type": exit_type, "params": {}}

        params = {}

        if entry_type == "trend_ema_cross":
            params["ema_fast"] = random.randint(5, 20)
            params["ema_slow"] = random.randint(21, 50)
        elif entry_type == "breakout_donchian":
            params["donchian_period"] = random.choice([10, 20, 30, 40, 50])
        elif entry_type == "mean_reversion_rsi":
            params["rsi_period"] = 14
            params["rsi_oversold"] = random.choice([20, 25, 30])
            params["rsi_overbought"] = random.choice([70, 75, 80])

        if exit_type == "atr_stop":
            params["atr_period"] = 14
            params["atr_multiplier"] = random.choice([1.5, 2.0, 3.0])
        elif exit_type == "time_stop":
            params["max_bars"] = random.choice([12, 24, 36]) # 1-3 hours on 5m
        elif exit_type == "fixed_rr":
             params["stop_loss_pct"] = random.choice([0.5, 1.0])
             params["take_profit_pct"] = params["stop_loss_pct"] * random.choice([1.5, 2.0])

        # Generate ID
        spec = json.dumps({
            "entry": entry_rule,
            "exit": exit_rule,
            "filters": filters,
            "params": params,
            "timeframe": timeframe
        }, sort_keys=True)
        sid = hashlib.md5(spec.encode()).hexdigest()[:8]

        return StrategyConfig(
            id=sid,
            entry_rules=[entry_rule],
            exit_rules=[exit_rule],
            filters=filters,
            params=params,
            timeframe=timeframe
        )

