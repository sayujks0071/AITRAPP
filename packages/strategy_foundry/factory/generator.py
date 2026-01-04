import random
from typing import List, Dict, Any
from .grammar import Strategy
from .parameter_space import get_random_params

BLOCK_TYPES = [
    {"type": "ema_cross", "category": "entry"},
    {"type": "rsi_reversion", "category": "entry"},
    {"type": "supertrend_trend", "category": "entry"},
    {"type": "donchian_breakout", "category": "entry"},
    {"type": "adx_filter", "category": "entry"}, # Used as filter/entry condition
    {"type": "stop_loss_pct", "category": "risk"},
    {"type": "trailing_stop_pct", "category": "risk"},
    {"type": "time_stop", "category": "risk"},
    {"type": "take_profit_pct", "category": "risk"}
]

def generate_candidates(n: int) -> List[Strategy]:
    """
    Generate N random strategy candidates.
    """
    candidates = []
    seen_ids = set()

    attempts = 0
    while len(candidates) < n and attempts < n * 5:
        attempts += 1

        # Compose a strategy
        # 1-2 Entry blocks
        # 1-2 Risk blocks

        blocks = []

        # Entry
        num_entries = random.randint(1, 2)
        entry_choices = [b for b in BLOCK_TYPES if b["category"] == "entry"]
        selected_entries = random.sample(entry_choices, num_entries)

        for entry in selected_entries:
            params = get_random_params(entry["type"])
            blocks.append({
                "type": entry["type"],
                "category": "entry",
                "params": params
            })

        # Risk
        num_risk = random.randint(1, 2)
        risk_choices = [b for b in BLOCK_TYPES if b["category"] == "risk"]
        selected_risks = random.sample(risk_choices, num_risk)

        for risk in selected_risks:
            params = get_random_params(risk["type"])
            blocks.append({
                "type": risk["type"],
                "category": "risk",
                "params": params
            })

        config = {"blocks": blocks}
        strategy = Strategy(config)

        if strategy.id not in seen_ids:
            seen_ids.add(strategy.id)
            candidates.append(strategy)

    return candidates
