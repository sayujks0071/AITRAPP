from enum import Enum
import random
from typing import Any, Dict, List

class StrategyType(Enum):
    EMA_CROSS = "EMA_CROSS"
    RSI_REVERSION = "RSI_REVERSION"
    DONCHIAN_BREAKOUT = "DONCHIAN_BREAKOUT"
    SUPERTREND = "SUPERTREND"

class FilterType(Enum):
    NONE = "NONE"
    RSI = "RSI"
    ADX = "ADX"
    REGIME_SMA = "REGIME_SMA"

class StopType(Enum):
    ATR = "ATR"
    TRAILING_ATR = "TRAILING_ATR"
    TIME = "TIME"

class ParameterSpace:
    """Defines valid ranges for parameters"""

    @staticmethod
    def get_ema_cross_params():
        fast = random.choice([5, 9, 10, 20])
        slow = random.choice([20, 50, 100, 200])
        if fast >= slow: fast, slow = slow, fast
        if fast == slow: slow += 10
        return {"fast": fast, "slow": slow}

    @staticmethod
    def get_rsi_reversion_params():
        return {
            "period": random.choice([7, 14, 21]),
            "lower": random.choice([20, 25, 30, 35]),
            "upper": random.choice([65, 70, 75, 80])
        }

    @staticmethod
    def get_donchian_params():
        return {"period": random.choice([10, 20, 55])}

    @staticmethod
    def get_supertrend_params():
        return {
            "period": random.choice([7, 10, 14]),
            "multiplier": random.choice([2.0, 3.0, 4.0])
        }

    @staticmethod
    def get_filter_params(ft: FilterType):
        if ft == FilterType.RSI:
            return {
                "type": "RSI",
                "params": {
                    "period": random.choice([14]),
                    "mode": random.choice(["below", "above"]),
                    "threshold": random.choice([30, 50, 70])
                }
            }
        elif ft == FilterType.ADX:
            return {
                "type": "ADX",
                "params": {
                    "period": 14,
                    "threshold": random.choice([20, 25, 30])
                }
            }
        elif ft == FilterType.REGIME_SMA:
            return {
                "type": "REGIME_SMA",
                "params": {"period": 200}
            }
        return None

    @staticmethod
    def get_stop_params(st: StopType):
        if st == StopType.ATR:
            return {
                "type": "ATR",
                "params": {
                    "period": 14,
                    "sl_mult": random.choice([1.5, 2.0, 3.0]),
                    "tp_mult": random.choice([2.0, 3.0, 5.0]) # Optional TP
                }
            }
        elif st == StopType.TRAILING_ATR:
            return {
                "type": "TRAILING_ATR",
                "params": {
                    "mult": random.choice([2.0, 3.0, 4.0])
                }
            }
        elif st == StopType.TIME:
            return {
                "type": "TIME",
                "params": {"max_bars": random.choice([5, 10, 20])}
            }
        return {"type": "NONE", "params": {}}
