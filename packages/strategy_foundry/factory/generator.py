import random
import hashlib
import json
from typing import List
from .grammar import StrategyCandidate

class StrategyGenerator:
    """
    Generates random Strategy Candidates based on a parameter space.
    """

    def generate_candidates(self, n: int = 50) -> List[StrategyCandidate]:
        candidates = []
        seen_hashes = set()

        while len(candidates) < n:
            params = self._random_params()

            # Create ID
            param_str = json.dumps(params, sort_keys=True)
            strat_id = hashlib.sha256(param_str.encode()).hexdigest()[:12]

            if strat_id in seen_hashes:
                continue

            seen_hashes.add(strat_id)

            # Generate description
            desc = self._describe(params)

            candidate = StrategyCandidate(
                strategy_id=strat_id,
                params=params,
                source_code=desc
            )
            candidates.append(candidate)

        return candidates

    def _random_params(self) -> dict:
        p = {}

        # 1. Entry Logic
        p["entry_type"] = random.choice(["supertrend", "ema_cross", "donchian_breakout", "rsi_reversal", "bb_reversion"])

        # 2. Filters
        p["use_adx_filter"] = random.choice([True, False])
        p["adx_threshold"] = random.choice([15, 20, 25])

        # 3. Parameters for indicators (implied fixed mostly, but we can vary thresholds)
        if p["entry_type"] == "rsi_reversal":
            p["rsi_lower"] = random.choice([20, 25, 30, 35])

        # 4. Risk / Exits
        p["stop_loss_pct"] = random.choice([1.0, 2.0, 3.0, 5.0])

        # Take profit: often better to let run, so 50% chance of being 0 (no TP)
        p["take_profit_pct"] = random.choice([0.0, 0.0, 5.0, 10.0])

        # Trailing
        if random.random() < 0.5:
            p["trailing_stop_activation_pct"] = random.choice([1.0, 2.0])
            p["trailing_stop_callback_pct"] = random.choice([0.5, 1.0])
        else:
            p["trailing_stop_activation_pct"] = 0.0
            p["trailing_stop_callback_pct"] = 0.0

        # Time exit
        p["max_bars_hold"] = random.choice([0, 0, 0, 5, 10, 20])

        # Direction
        p["direction"] = "long_only" # Enforce long only for now as per plan defaults

        return p

    def _describe(self, p: dict) -> str:
        parts = []
        parts.append(f"Entry: {p['entry_type']}")
        if p['use_adx_filter']:
            parts.append(f"Filter: ADX>{p['adx_threshold']}")

        parts.append(f"Risk: SL {p['stop_loss_pct']}%")
        if p['take_profit_pct'] > 0:
            parts.append(f"TP {p['take_profit_pct']}%")

        if p['trailing_stop_activation_pct'] > 0:
            parts.append(f"Trail: Act {p['trailing_stop_activation_pct']}% / Call {p['trailing_stop_callback_pct']}%")

        if p['max_bars_hold'] > 0:
            parts.append(f"TimeExit: {p['max_bars_hold']} bars")

        return " | ".join(parts)
