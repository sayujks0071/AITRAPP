"""
Strategy Grammar and Factory
Defines the building blocks for strategies and generates random combinations.
"""
import random
import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class StrategyConfig:
    id: str = ""
    entry_block: str = ""
    entry_params: Dict[str, Any] = field(default_factory=dict)
    exit_block: str = ""
    exit_params: Dict[str, Any] = field(default_factory=dict)
    risk_block: str = ""
    risk_params: Dict[str, Any] = field(default_factory=dict)
    filter_block: str = ""
    filter_params: Dict[str, Any] = field(default_factory=dict)

    def generate_id(self):
        """Generate a stable ID hash based on config"""
        payload = {
            "entry": self.entry_block,
            "entry_p": self.entry_params,
            "exit": self.exit_block,
            "exit_p": self.exit_params,
            "risk": self.risk_block,
            "risk_p": self.risk_params,
            "filter": self.filter_block,
            "filter_p": self.filter_params
        }
        s = json.dumps(payload, sort_keys=True)
        self.id = hashlib.md5(s.encode()).hexdigest()[:12]

class Grammar:
    # Entry Blocks
    ENTRY_BLOCKS = [
        "breakout_donchian",
        "breakout_orb",
        "trend_ema_cross",
        "mean_reversion_rsi"
    ]

    # Exit/Risk Blocks
    EXIT_BLOCKS = [
        "simple_target_stop",
        "trailing_stop_atr"
    ]

    RISK_BLOCKS = [
        "atr_stop",
        "percent_stop"
    ]

    FILTERS = [
        "none",
        "trend_filter_ema",
        "time_filter_chop"
    ]

    @staticmethod
    def get_params(block_name: str):
        if block_name == "breakout_donchian":
            return {"period": [10, 20, 50]}
        elif block_name == "breakout_orb":
            return {"minutes": [15, 30, 60]}
        elif block_name == "trend_ema_cross":
            return {"fast": [5, 9, 13], "slow": [20, 50]}
        elif block_name == "mean_reversion_rsi":
            return {"period": [14], "lower": [30, 25], "upper": [70, 75]}

        elif block_name == "simple_target_stop":
            return {"rr_ratio": [1.5, 2.0, 3.0]}
        elif block_name == "trailing_stop_atr":
            return {"multiplier": [2.0, 3.0]}

        elif block_name == "atr_stop":
            return {"multiplier": [1.5, 2.0, 2.5]}
        elif block_name == "percent_stop":
            return {"pct": [0.5, 1.0]}

        elif block_name == "trend_filter_ema":
             return {"period": [50, 200]}
        elif block_name == "time_filter_chop":
             return {"start_time": ["09:45"]} # Avoid first 30m

        return {}

    @staticmethod
    def sample_params(block_name: str) -> Dict[str, Any]:
        params = Grammar.get_params(block_name)
        sampled = {}
        for k, v in params.items():
            sampled[k] = random.choice(v)
        return sampled

class StrategyGenerator:
    @staticmethod
    def generate_population(n: int) -> List[StrategyConfig]:
        population = []
        seen_ids = set()

        while len(population) < n:
            entry = random.choice(Grammar.ENTRY_BLOCKS)
            exit_ = random.choice(Grammar.EXIT_BLOCKS)
            risk = random.choice(Grammar.RISK_BLOCKS)
            filt = random.choice(Grammar.FILTERS)

            cfg = StrategyConfig(
                entry_block=entry,
                entry_params=Grammar.sample_params(entry),
                exit_block=exit_,
                exit_params=Grammar.sample_params(exit_),
                risk_block=risk,
                risk_params=Grammar.sample_params(risk),
                filter_block=filt,
                filter_params=Grammar.sample_params(filt)
            )
            cfg.generate_id()

            if cfg.id not in seen_ids:
                population.append(cfg)
                seen_ids.add(cfg.id)

        return population
