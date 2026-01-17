from typing import Dict, List, Any
import random

class ParameterSpace:
    """
    Defines the search space for strategy parameters.
    """

    INDICATORS = ["sma", "ema", "rsi", "adx", "atr", "supertrend", "bollinger", "donchian"]

    # Intraday friendly periods
    PERIODS = [5, 10, 14, 20, 50, 200]
    MULTIPLIERS = [1.5, 2.0, 3.0]
    THRESHOLDS = {
        "rsi": [30, 70, 40, 60],
        "adx": [20, 25, 30]
    }

    ENTRY_TYPES = [
        "trend_following",
        "mean_reversion",
        "breakout"
    ]

    RISK_MODELS = {
        "stop_loss_atr": [1.0, 1.5, 2.0, 3.0],
        "take_profit_atr": [2.0, 3.0, 4.0, 6.0],
        "trailing_stop": [False, True]
    }

    @classmethod
    def get_random_period(cls) -> int:
        return random.choice(cls.PERIODS)

    @classmethod
    def get_random_multiplier(cls) -> float:
        return random.choice(cls.MULTIPLIERS)

    @classmethod
    def get_random_threshold(cls, indicator: str) -> float:
        return random.choice(cls.THRESHOLDS.get(indicator, [0]))
