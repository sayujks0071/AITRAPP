"""
Strategy Grammar and Generator
"""
import random
import hashlib
import json

class StrategyGrammar:
    ENTRY_TYPES = [
        "trend_ema_cross",
        "trend_supertrend",
        "mean_rev_rsi",
        "mean_rev_bb",
        "breakout_donchian",
        "volatility_expansion"
    ]

    EXIT_TYPES = [
        "time_stop",
        "atr_stop",
        "fixed_tp",
        "trailing_stop"
    ]

    FILTERS = [
        "adx_filter",
        "ema_filter_long",
        "rsi_filter"
    ]

    @staticmethod
    def random_strategy(max_blocks=5, max_tunables=10):
        strategy = {
            "entry": {},
            "exit": {},
            "filters": [],
            "id": ""
        }

        # Pick Entry
        entry_type = random.choice(StrategyGrammar.ENTRY_TYPES)
        strategy["entry"] = StrategyGrammar._get_params(entry_type)

        # Pick Exit (1 or more)
        # Always include at least one stop mechanism
        exit_type = random.choice([e for e in StrategyGrammar.EXIT_TYPES if "stop" in e])
        strategy["exit"][exit_type] = StrategyGrammar._get_params(exit_type)

        # Optional second exit (e.g. TP)
        if random.random() > 0.5:
            tp_type = "fixed_tp"
            strategy["exit"][tp_type] = StrategyGrammar._get_params(tp_type)

        # Optional Filters
        if random.random() > 0.3:
            filter_type = random.choice(StrategyGrammar.FILTERS)
            strategy["filters"].append({
                "type": filter_type,
                "params": StrategyGrammar._get_params(filter_type)
            })

        # Generate ID
        s_str = json.dumps(strategy, sort_keys=True)
        strategy["id"] = hashlib.sha256(s_str.encode()).hexdigest()[:16]

        return strategy

    @staticmethod
    def _get_params(block_type):
        if block_type == "trend_ema_cross":
            return {"fast": random.choice([5,9,13,20]), "slow": random.choice([20,34,50,89])}
        elif block_type == "trend_supertrend":
            return {"period": random.choice([7,10,14]), "multiplier": random.choice([1.5, 2.0, 3.0])}
        elif block_type == "mean_rev_rsi":
            return {"period": 14, "lower": random.choice([20,25,30]), "upper": random.choice([70,75,80])}
        elif block_type == "mean_rev_bb":
            return {"period": 20, "std": 2.0}
        elif block_type == "breakout_donchian":
            return {"period": random.choice([10,20,40])}
        elif block_type == "volatility_expansion":
            return {"lookback": random.choice([5, 10]), "threshold": 1.5}

        elif block_type == "time_stop":
            return {"bars": random.choice([3, 6, 12, 24])}
        elif block_type == "atr_stop":
            return {"period": 14, "multiple": random.choice([1.5, 2.0, 3.0])}
        elif block_type == "fixed_tp":
            return {"multiple_of_risk": random.choice([1.5, 2.0, 3.0])} # R:R
        elif block_type == "trailing_stop":
            return {"activation": 1.0, "delta": 0.5} # In ATR multiples usually

        elif block_type == "adx_filter":
            return {"period": 14, "threshold": random.choice([20, 25])}
        elif block_type == "ema_filter_long":
            return {"period": random.choice([100, 200])}
        elif block_type == "rsi_filter":
            return {"min": 40, "max": 60}

        return {}
