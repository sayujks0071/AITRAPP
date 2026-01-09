from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import random
import hashlib
import json

@dataclass
class StrategyCandidate:
    id: str
    grammar: Dict[str, Any]
    params: Dict[str, Any]
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def rule_summary(self) -> str:
        """Human readable summary"""
        s = f"Strategy {self.id[:8]}:\n"
        s += f"  Entry: {self.grammar.get('entry_type')} (Filter: {self.grammar.get('filter_type')})\n"
        s += f"  Exit: {self.grammar.get('exit_type')}\n"
        s += f"  Stop: {self.grammar.get('stop_type')}\n"
        return s

class StrategyGrammar:
    """
    Defines the search space for strategies.

    Blocks:
    1. Trend (EMA Cross, Supertrend)
    2. Mean Reversion (RSI, BB)
    3. Filters (ADX, Regime)
    4. Exits (Target, Stop, Trailing)
    """

    ENTRY_TYPES = ["EMA_CROSS", "SUPERTREND_FLIP", "RSI_REVERSION", "BB_REVERSION", "DONCHIAN_BREAKOUT"]
    FILTER_TYPES = ["NONE", "ADX_FILTER", "SMA_REGIME", "RSI_FILTER"]
    EXIT_TYPES = ["FIXED_RR", "TRAILING_ATR", "TIME_EXIT", "INDICATOR_EXIT"]
    STOP_TYPES = ["ATR_STOP", "PCT_STOP", "LOW_HIGH_STOP"]

    @staticmethod
    def generate_random() -> StrategyCandidate:
        grammar = {
            "entry_type": random.choice(StrategyGrammar.ENTRY_TYPES),
            "filter_type": random.choice(StrategyGrammar.FILTER_TYPES),
            "exit_type": random.choice(StrategyGrammar.EXIT_TYPES),
            "stop_type": random.choice(StrategyGrammar.STOP_TYPES)
        }

        params = StrategyGrammar.generate_params(grammar)

        # Create stable ID
        grammar_str = json.dumps(grammar, sort_keys=True)
        params_str = json.dumps(params, sort_keys=True)
        raw_id = f"{grammar_str}|{params_str}"
        id_hash = hashlib.sha256(raw_id.encode()).hexdigest()

        return StrategyCandidate(id=id_hash, grammar=grammar, params=params)

    @staticmethod
    def generate_params(grammar: Dict[str, str]) -> Dict[str, Any]:
        p = {}

        # Entry Params
        if grammar["entry_type"] == "EMA_CROSS":
            p["ema_fast"] = random.choice([5, 9, 10, 20])
            p["ema_slow"] = random.choice([20, 50, 100, 200])
            if p["ema_fast"] >= p["ema_slow"]: p["ema_fast"], p["ema_slow"] = p["ema_slow"], p["ema_fast"]

        elif grammar["entry_type"] == "SUPERTREND_FLIP":
            p["st_period"] = random.choice([7, 10, 14])
            p["st_multiplier"] = random.choice([1.0, 2.0, 3.0])

        elif grammar["entry_type"] == "RSI_REVERSION":
            p["rsi_period"] = 14
            p["rsi_lower"] = random.choice([20, 25, 30])
            p["rsi_upper"] = random.choice([70, 75, 80])

        elif grammar["entry_type"] == "BB_REVERSION":
            p["bb_period"] = 20
            p["bb_std"] = 2.0

        elif grammar["entry_type"] == "DONCHIAN_BREAKOUT":
            p["donchian_period"] = random.choice([20, 50, 55])

        # Filter Params
        if grammar["filter_type"] == "ADX_FILTER":
            p["adx_period"] = 14
            p["adx_threshold"] = random.choice([20, 25])
        elif grammar["filter_type"] == "SMA_REGIME":
            p["regime_sma"] = 200
        elif grammar["filter_type"] == "RSI_FILTER":
            p["rsi_filter_period"] = 14

        # Stop Params
        if grammar["stop_type"] == "ATR_STOP":
            p["stop_atr_period"] = 14
            p["stop_atr_mult"] = random.choice([1.5, 2.0, 3.0])
        elif grammar["stop_type"] == "PCT_STOP":
            p["stop_pct"] = random.choice([0.01, 0.02, 0.05])
        elif grammar["stop_type"] == "LOW_HIGH_STOP":
            p["stop_lookback"] = random.choice([3, 5])

        # Exit Params
        if grammar["exit_type"] == "FIXED_RR":
            p["rr_ratio"] = random.choice([1.5, 2.0, 3.0])
        elif grammar["exit_type"] == "TRAILING_ATR":
            p["trail_atr_period"] = 14
            p["trail_atr_mult"] = random.choice([2.0, 3.0])
        elif grammar["exit_type"] == "TIME_EXIT":
            p["max_bars"] = random.choice([5, 10, 20])

        return p
