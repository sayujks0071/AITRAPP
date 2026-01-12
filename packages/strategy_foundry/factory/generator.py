import random
from typing import List, Dict, Any
from .grammar import StrategyCandidate

class StrategyGenerator:
    def __init__(self):
        pass

    def generate_candidates(self, n: int = 10) -> List[StrategyCandidate]:
        candidates = []
        seen_ids = set()

        while len(candidates) < n:
            cand = self._generate_single()
            if cand.id not in seen_ids:
                candidates.append(cand)
                seen_ids.add(cand.id)

        return candidates

    def _generate_single(self) -> StrategyCandidate:
        entry_type = random.choice(["trend_ema_cross", "breakout_donchian", "mean_rev_rsi", "supertrend"])

        entry_logic = {"type": entry_type}
        params = {}

        if entry_type == "trend_ema_cross":
            params["ema_fast"] = random.choice([9, 13, 20])
            params["ema_slow"] = random.choice([21, 34, 50, 89])
            if params["ema_fast"] >= params["ema_slow"]:
                params["ema_fast"], params["ema_slow"] = params["ema_slow"] + 1, params["ema_fast"] + 5
            params["adx_filter"] = random.choice([True, False])
            if params["adx_filter"]:
                params["adx_period"] = 14
                params["adx_threshold"] = random.choice([20, 25])

        elif entry_type == "breakout_donchian":
            params["donchian_period"] = random.choice([10, 20, 40, 60])
            params["filter_ma"] = random.choice([True, False])
            if params["filter_ma"]:
                params["ma_period"] = 200

        elif entry_type == "mean_rev_rsi":
            params["rsi_period"] = 14
            params["rsi_oversold"] = random.choice([20, 25, 30])
            params["rsi_overbought"] = random.choice([70, 75, 80])

        elif entry_type == "supertrend":
            params["st_period"] = random.choice([7, 10, 14])
            params["st_multiplier"] = random.choice([1.0, 2.0, 3.0])

        # Exit Logic
        exit_logic = {
            "stop_loss_type": "atr",
            "take_profit_type": random.choice(["risk_reward", "none"]),
            "time_exit": True # Always enforce EOD
        }

        params["sl_atr_period"] = 14
        params["sl_atr_mult"] = random.choice([1.5, 2.0, 3.0])

        if exit_logic["take_profit_type"] == "risk_reward":
            params["tp_risk_reward"] = random.choice([1.5, 2.0, 3.0])

        params["flat_time"] = "15:25"

        cand = StrategyCandidate(
            id="",
            entry_logic=entry_logic,
            exit_logic=exit_logic,
            params=params
        )
        cand.generate_id()
        return cand
