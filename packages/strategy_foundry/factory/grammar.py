"""
Strategy Grammar and Generator.
Defines the building blocks for strategies.
"""
import random
import hashlib
import json
from typing import Dict, Any, List

# Parameter Ranges
PARAM_RANGES = {
    "ema_fast": range(5, 50, 5),
    "ema_slow": range(20, 200, 10),
    "rsi_period": [14],
    "rsi_lower": range(20, 40, 5),
    "rsi_upper": range(60, 80, 5),
    "adx_threshold": range(15, 30, 5),
    "atr_stop_mult": [1.0, 1.5, 2.0, 2.5, 3.0],
    "max_hold_days": [3, 5, 10, 20],
    "donchian_period": range(10, 60, 10),
    "bb_std": [1.5, 2.0, 2.5]
}

class StrategyGrammar:
    @staticmethod
    def get_random_param(name: str):
        if name in PARAM_RANGES:
            return random.choice(list(PARAM_RANGES[name]))
        return None

    @staticmethod
    def trend_ema_cross():
        fast = StrategyGrammar.get_random_param("ema_fast")
        slow = StrategyGrammar.get_random_param("ema_slow")
        if fast >= slow:
            fast, slow = slow, fast
            if fast == slow: slow += 5
        return {
            "type": "ENTRY",
            "subtype": "EMA_CROSS",
            "params": {"fast": fast, "slow": slow}
        }

    @staticmethod
    def trend_donchian_breakout():
        return {
            "type": "ENTRY",
            "subtype": "DONCHIAN_BREAKOUT",
            "params": {"period": StrategyGrammar.get_random_param("donchian_period")}
        }

    @staticmethod
    def mean_rev_rsi():
        return {
            "type": "ENTRY",
            "subtype": "RSI_REVERSION",
            "params": {
                "period": StrategyGrammar.get_random_param("rsi_period"),
                "lower": StrategyGrammar.get_random_param("rsi_lower"),
                "upper": StrategyGrammar.get_random_param("rsi_upper")
            }
        }

    @staticmethod
    def filter_adx():
        return {
            "type": "FILTER",
            "subtype": "ADX_FILTER",
            "params": {"threshold": StrategyGrammar.get_random_param("adx_threshold")}
        }

    @staticmethod
    def exit_atr_stop():
        return {
            "type": "EXIT",
            "subtype": "ATR_STOP",
            "params": {"multiplier": StrategyGrammar.get_random_param("atr_stop_mult")}
        }

    @staticmethod
    def exit_time_stop():
        return {
            "type": "EXIT",
            "subtype": "TIME_STOP",
            "params": {"days": StrategyGrammar.get_random_param("max_hold_days")}
        }

def generate_candidate() -> Dict[str, Any]:
    """Generates a random strategy configuration."""

    # Decide Strategy Type
    strat_type = random.choice(["TREND", "MEAN_REVERSION"])

    blocks = []

    if strat_type == "TREND":
        # Core Entry
        if random.random() < 0.7:
            blocks.append(StrategyGrammar.trend_ema_cross())
        else:
            blocks.append(StrategyGrammar.trend_donchian_breakout())

        # Optional Filter
        if random.random() < 0.5:
            blocks.append(StrategyGrammar.filter_adx())

    elif strat_type == "MEAN_REVERSION":
        blocks.append(StrategyGrammar.mean_rev_rsi())

    # Risk Management (Exits)
    # Always add an ATR stop
    blocks.append(StrategyGrammar.exit_atr_stop())

    # Optional Time Stop
    if random.random() < 0.5:
        blocks.append(StrategyGrammar.exit_time_stop())

    # Construct Config
    config = {
        "blocks": blocks,
        "strategy_type": strat_type
    }

    # Generate ID
    config_str = json.dumps(config, sort_keys=True)
    config_hash = hashlib.md5(config_str.encode()).hexdigest()
    config["id"] = config_hash

    return config

def summarize_rules(config: Dict[str, Any]) -> str:
    summary = []
    for block in config.get("blocks", []):
        st = block['subtype']
        p = block['params']
        if st == "EMA_CROSS":
            summary.append(f"EMA Cross ({p['fast']}/{p['slow']})")
        elif st == "DONCHIAN_BREAKOUT":
            summary.append(f"Donchian ({p['period']}) Breakout")
        elif st == "RSI_REVERSION":
            summary.append(f"RSI({p['period']}) < {p['lower']} Buy")
        elif st == "ADX_FILTER":
            summary.append(f"ADX > {p['threshold']}")
        elif st == "ATR_STOP":
            summary.append(f"ATR Stop {p['multiplier']}x")
        elif st == "TIME_STOP":
            summary.append(f"Time Stop {p['days']}d")

    return " + ".join(summary)
