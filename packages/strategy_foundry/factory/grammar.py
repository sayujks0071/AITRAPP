from typing import Dict, Any, List
import random
import hashlib
import json

class StrategyConfig:
    def __init__(self, name: str, blocks: List[Dict[str, Any]], params: Dict[str, Any]):
        self.name = name
        self.blocks = blocks
        self.params = params

    def get_id(self) -> str:
        # Stable ID based on blocks and params
        s = json.dumps({"blocks": self.blocks, "params": self.params}, sort_keys=True)
        return hashlib.md5(s.encode()).hexdigest()

    def to_dict(self):
        return {
            "id": self.get_id(),
            "name": self.name,
            "blocks": self.blocks,
            "params": self.params,
            "rule_summary": self.describe()
        }

    def describe(self) -> str:
        # Human readable summary
        desc = []
        for b in self.blocks:
            desc.append(f"{b['type']}({b.get('subtype', '')})")
        return " + ".join(desc)

class Grammar:
    # Trend: EMA/SMA cross, ADX filter, Supertrend, Donchian breakout
    # Mean reversion: RSI reversion, Bollinger mean reversion
    # Volatility/risk: ATR stop, time stop, trailing stop, max bars in trade
    # Filters: regime filter, volatility filter, session filter

    TREND_BLOCKS = [
        {"type": "trend", "subtype": "ema_cross", "param_keys": ["ema_fast", "ema_slow"]},
        {"type": "trend", "subtype": "supertrend", "param_keys": ["st_period", "st_multiplier"]},
        {"type": "trend", "subtype": "donchian", "param_keys": ["donchian_period"]},
    ]

    MEAN_REV_BLOCKS = [
        {"type": "mean_rev", "subtype": "rsi", "param_keys": ["rsi_period", "rsi_oversold", "rsi_overbought"]},
        {"type": "mean_rev", "subtype": "bollinger", "param_keys": ["bb_period", "bb_std"]},
    ]

    EXIT_BLOCKS = [
        {"type": "exit", "subtype": "atr_stop", "param_keys": ["atr_period", "stop_atr_mult"]},
        {"type": "exit", "subtype": "time_stop", "param_keys": ["max_bars"]},
        {"type": "exit", "subtype": "trailing_stop", "param_keys": ["trail_percent"]},
    ]

    FILTERS = [
        {"type": "filter", "subtype": "adx", "param_keys": ["adx_period", "adx_threshold"]},
        {"type": "filter", "subtype": "long_only", "param_keys": []} # Global filter often
    ]

    @staticmethod
    def get_random_strategy() -> StrategyConfig:
        # Compose 2-4 blocks
        # Usually 1 Entry (Trend or MeanRev) + 1 Exit + Optional Filter

        blocks = []
        params = {}

        # Decide Entry Type
        entry_type = random.choice(["trend", "mean_rev"])

        if entry_type == "trend":
            b = random.choice(Grammar.TREND_BLOCKS)
            blocks.append(b)
            # Add filter sometimes
            if random.random() < 0.3:
                f = random.choice(Grammar.FILTERS)
                blocks.append(f)
        else:
            b = random.choice(Grammar.MEAN_REV_BLOCKS)
            blocks.append(b)

        # Always add exit
        e = random.choice(Grammar.EXIT_BLOCKS)
        blocks.append(e)

        # Generate Params
        for b in blocks:
            for k in b["param_keys"]:
                params[k] = Grammar.sample_param(k)

        # Name
        name = f"Auto_{entry_type}_{len(blocks)}blocks"

        return StrategyConfig(name, blocks, params)

    @staticmethod
    def sample_param(key: str):
        # Define ranges
        ranges = {
            "ema_fast": [9, 10, 12, 15, 20],
            "ema_slow": [20, 30, 50, 100, 200],
            "st_period": [7, 10, 14],
            "st_multiplier": [1.5, 2.0, 3.0, 4.0],
            "donchian_period": [10, 20, 40, 55],
            "rsi_period": [7, 14, 21],
            "rsi_oversold": [20, 25, 30, 35],
            "rsi_overbought": [65, 70, 75, 80],
            "bb_period": [15, 20, 25],
            "bb_std": [1.5, 2.0, 2.5],
            "atr_period": [10, 14, 20],
            "stop_atr_mult": [1.0, 1.5, 2.0, 3.0],
            "max_bars": [3, 5, 10, 20],
            "trail_percent": [0.01, 0.02, 0.03, 0.05],
            "adx_period": [14],
            "adx_threshold": [20, 25, 30]
        }

        if key in ranges:
            return random.choice(ranges[key])
        return 0
