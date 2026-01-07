import random
from typing import Dict, Any, List

class ParameterSpace:
    """Defines valid ranges for parameters"""
    EMA_PERIODS = [10, 20, 50, 100, 200]
    RSI_PERIODS = [7, 14, 21]
    RSI_LEVELS = [20, 30, 40, 60, 70, 80]

    @staticmethod
    def get_random_trend_params() -> Dict[str, Any]:
        fast = random.choice([10, 20, 50])
        slow = random.choice([50, 100, 200])
        while fast >= slow:
            fast = random.choice([10, 20, 50])
            slow = random.choice([50, 100, 200])

        return {
            "type": "SimpleTrend",
            "ema_fast": fast,
            "ema_slow": slow,
            "rsi_period": random.choice([14]),
            "rsi_min": random.choice([40, 45, 50]),
            "rsi_max": random.choice([50, 55, 60]),
            "stop_atr_mult": random.choice([1.5, 2.0, 3.0]),
        }

    @staticmethod
    def get_random_mean_rev_params() -> Dict[str, Any]:
        return {
            "type": "MeanReversion",
            "rsi_lower": random.choice([20, 25, 30, 35]),
            "rsi_upper": random.choice([65, 70, 75, 80]),
            "stop_atr_mult": random.choice([2.0, 3.0, 4.0]),
        }
