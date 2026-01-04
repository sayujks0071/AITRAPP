import random
from typing import Dict, Any

def get_random_params(block_type: str) -> Dict[str, Any]:
    if block_type == "ema_cross":
        fast = random.randint(5, 50)
        slow = random.randint(fast + 10, 200)
        return {"fast": fast, "slow": slow}

    elif block_type == "rsi_reversion":
        period = random.choice([7, 14])
        threshold = random.randint(20, 40)
        return {"period": period, "lower_threshold": threshold}

    elif block_type == "supertrend_trend":
        period = random.choice([7, 10, 14])
        multiplier = random.choice([2.0, 3.0, 4.0])
        return {"period": period, "multiplier": multiplier}

    elif block_type == "donchian_breakout":
        period = random.choice([10, 20, 50, 55])
        return {"period": period}

    elif block_type == "adx_filter":
        period = 14
        threshold = random.randint(20, 30)
        return {"period": period, "threshold": threshold}

    elif block_type == "stop_loss_pct":
        return {"pct": round(random.uniform(0.02, 0.10), 3)}

    elif block_type == "trailing_stop_pct":
        return {"pct": round(random.uniform(0.03, 0.15), 3)}

    elif block_type == "time_stop":
        return {"bars": random.randint(3, 20)}

    elif block_type == "take_profit_pct":
        return {"pct": round(random.uniform(0.05, 0.30), 3)}

    return {}
