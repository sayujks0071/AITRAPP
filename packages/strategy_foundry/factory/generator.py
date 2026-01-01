"""Strategy Generator"""
import random
import hashlib
import json
from typing import List, Dict, Any
from datetime import datetime
from packages.strategy_foundry.factory.parameter_space import PARAM_SPACE

class StrategyGenerator:
    def __init__(self, seed: int = None):
        if seed is None:
            # Seed based on hour to ensure deterministic set per run if needed,
            # or purely random if we want exploration.
            # Plan says "random seed tied to hour timestamp".
            seed = int(datetime.now().timestamp() / 3600)
        random.seed(seed)

    def generate_candidates(self, n: int = 50) -> List[Dict[str, Any]]:
        candidates = []
        seen_hashes = set()

        while len(candidates) < n:
            logic = random.choice(PARAM_SPACE["logic_type"])
            params = self._sample_params(logic)

            candidate = {
                "logic_type": logic,
                "params": params,
                "created_at": datetime.now().isoformat()
            }

            # ID Generation
            c_str = json.dumps(candidate, sort_keys=True)
            c_hash = hashlib.sha256(c_str.encode()).hexdigest()

            if c_hash not in seen_hashes:
                candidate["id"] = c_hash
                candidates.append(candidate)
                seen_hashes.add(c_hash)

        return candidates

    def _sample_params(self, logic_type: str) -> Dict[str, Any]:
        params = {}
        if logic_type == "trend_crossover":
            params["ma_fast"] = random.choice(PARAM_SPACE["ma_fast"])
            params["ma_slow"] = random.choice(PARAM_SPACE["ma_slow"])
            # Ensure fast < slow
            if params["ma_fast"] >= params["ma_slow"]:
                params["ma_fast"], params["ma_slow"] = params["ma_slow"], params["ma_fast"]
                if params["ma_fast"] == params["ma_slow"]:
                    params["ma_slow"] += 5

        elif logic_type == "rsi_mean_reversion":
            params["rsi_period"] = random.choice(PARAM_SPACE["rsi_period"])
            params["rsi_overbought"] = random.choice(PARAM_SPACE["rsi_overbought"])
            params["rsi_oversold"] = random.choice(PARAM_SPACE["rsi_oversold"])

        elif logic_type == "supertrend_follow":
            params["st_period"] = random.choice(PARAM_SPACE["st_period"])
            params["st_multiplier"] = random.choice(PARAM_SPACE["st_multiplier"])

        elif logic_type == "donchian_breakout":
            params["donchian_period"] = random.choice(PARAM_SPACE["donchian_period"])

        elif logic_type == "bollinger_mean_reversion":
            params["bb_period"] = random.choice(PARAM_SPACE["bb_period"])
            params["bb_std"] = random.choice(PARAM_SPACE["bb_std"])

        return params
