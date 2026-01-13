from typing import Dict, Any, List
import random
import hashlib
import json

class Grammar:
    """
    Strategy Grammar: defines valid blocks and how to compose them.
    """

    BLOCKS = {
        "trend": ["ema_cross", "supertrend", "donchian_breakout"],
        "mean_reversion": ["rsi_reversion", "bollinger_reversion"],
        "filter": ["adx_filter", "regime_filter"],
        "exit": ["atr_stop", "time_stop"]
    }

    @staticmethod
    def generate_random_strategy() -> Dict[str, Any]:
        """
        Generates a random strategy configuration.
        Structure:
        {
           "id": "hash",
           "entry": { type: "trend"|"mean_rev", name: "...", params: {...} },
           "filter": { name: "...", params: {...} } (optional),
           "exit": { name: "...", params: {...} }
        }
        """
        # Pick a style
        style = random.choice(["trend", "mean_reversion"])
        entry_name = random.choice(Grammar.BLOCKS[style])

        # Pick a filter (50% chance)
        use_filter = random.random() > 0.5
        filter_conf = None
        if use_filter:
            filter_name = random.choice(Grammar.BLOCKS["filter"])
            filter_conf = {"name": filter_name, "params": Grammar.get_random_params(filter_name)}

        # Pick an exit
        exit_name = random.choice(Grammar.BLOCKS["exit"])
        exit_conf = {"name": exit_name, "params": Grammar.get_random_params(exit_name)}

        entry_conf = {"type": style, "name": entry_name, "params": Grammar.get_random_params(entry_name)}

        strategy = {
            "entry": entry_conf,
            "filter": filter_conf,
            "exit": exit_conf
        }

        # Generate stable ID
        s_str = json.dumps(strategy, sort_keys=True)
        s_id = hashlib.md5(s_str.encode()).hexdigest()[:12]
        strategy["id"] = s_id

        return strategy

    @staticmethod
    def get_random_params(block_name: str) -> Dict[str, Any]:
        """Returns random parameters for a given block."""
        if block_name == "ema_cross":
            # Fast < Slow
            fast = random.randint(5, 50)
            slow = random.randint(fast + 10, 200)
            return {"fast": fast, "slow": slow}
        elif block_name == "supertrend":
            return {"period": random.choice([7, 10, 14]), "multiplier": random.choice([2.0, 3.0, 4.0])}
        elif block_name == "donchian_breakout":
            return {"period": random.randint(10, 60)}
        elif block_name == "rsi_reversion":
            return {"period": 14, "buy_threshold": random.randint(20, 40), "sell_threshold": random.randint(60, 80)}
        elif block_name == "bollinger_reversion":
            return {"period": 20, "std": 2.0}
        elif block_name == "adx_filter":
            return {"threshold": random.randint(20, 30)}
        elif block_name == "regime_filter":
            return {"ma_period": 200}
        elif block_name == "atr_stop":
            return {"multiplier": random.choice([1.0, 1.5, 2.0, 3.0]), "period": 14}
        elif block_name == "time_stop":
            return {"days": random.randint(5, 20)}
        return {}

class StrategyGenerator:
    def __init__(self, seed: int = None):
        if seed:
            random.seed(seed)

    def generate_candidates(self, n: int) -> List[Dict[str, Any]]:
        candidates = []
        seen = set()

        attempts = 0
        while len(candidates) < n and attempts < n * 5:
            strat = Grammar.generate_random_strategy()
            if strat["id"] not in seen:
                seen.add(strat["id"])
                candidates.append(strat)
            attempts += 1

        return candidates
