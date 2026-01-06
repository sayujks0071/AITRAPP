"""Strategy candidate generator"""
import random
import copy
from typing import List
from packages.strategy_foundry.factory.grammar import (
    StrategyCandidate, generate_id,
    ENTRY_TYPES, EXIT_TYPES, FILTER_TYPES, PARAM_RANGES
)

class StrategyGenerator:
    def __init__(self, timeframes: List[str] = ["5m", "15m"]):
        self.timeframes = timeframes

    def generate(self, count: int = 80) -> List[StrategyCandidate]:
        candidates = []
        seen_ids = set()

        while len(candidates) < count:
            c = self._create_random()
            c.id = generate_id(c)

            if c.id not in seen_ids:
                seen_ids.add(c.id)
                candidates.append(c)

        return candidates

    def _create_random(self) -> StrategyCandidate:
        tf = random.choice(self.timeframes)
        entry_type = random.choice(ENTRY_TYPES)
        exit_type = random.choice(EXIT_TYPES)

        # 0 to 2 filters
        num_filters = random.randint(0, 2)
        filters = []
        if num_filters > 0:
            # Pick random unique filters
            chosen_filters = random.sample(FILTER_TYPES, num_filters)
            for f_type in chosen_filters:
                filters.append({"type": f_type})

        params = {}

        # Populate Entry Params
        if entry_type == "ORB_BREAKOUT":
            params["orb_window"] = random.choice(PARAM_RANGES["orb_window_minutes"])
        elif entry_type == "DONCHIAN_BREAKOUT":
            params["donchian_period"] = random.choice(PARAM_RANGES["donchian_period"])
        elif entry_type == "RSI_REVERSION":
            params["rsi_period"] = random.choice(PARAM_RANGES["rsi_period"])
            params["rsi_ob"] = random.choice(PARAM_RANGES["rsi_overbought"])
            params["rsi_os"] = random.choice(PARAM_RANGES["rsi_oversold"])
        elif entry_type == "EMA_CROSS":
            f = random.choice(PARAM_RANGES["ema_fast"])
            s = random.choice([x for x in PARAM_RANGES["ema_slow"] if x > f])
            params["ema_fast"] = f
            params["ema_slow"] = s
        elif entry_type == "BOLLINGER_REVERSION":
            params["bb_period"] = random.choice(PARAM_RANGES["bb_period"])
            params["bb_std"] = random.choice(PARAM_RANGES["bb_std"])

        # Populate Exit Params
        if exit_type == "ATR_TRAIL":
            params["atr_period"] = random.choice(PARAM_RANGES["atr_period"])
            params["atr_mult"] = random.choice(PARAM_RANGES["atr_multiplier"])
        elif exit_type == "TIME_STOP":
            params["max_bars"] = random.choice(PARAM_RANGES["time_stop_bars"])
        elif exit_type == "FIXED_RR":
            params["atr_period"] = random.choice(PARAM_RANGES["atr_period"]) # For stop basis
            params["atr_mult_stop"] = 1.0 # Fixed 1ATR stop for base
            params["rr_ratio"] = random.choice(PARAM_RANGES["profit_target_rr"])

        # Filter Params
        for f in filters:
            if f["type"] == "TREND_EMA_1H":
                params["trend_ema"] = random.choice(PARAM_RANGES["trend_ema_period"])

        return StrategyCandidate(
            id="",
            entry_logic={"type": entry_type},
            exit_logic={"type": exit_type},
            filters=filters,
            timeframe=tf,
            params=params
        )
