"""
Parameter space definitions for strategy components.
"""
from typing import Dict, Any, List

class ParameterRange:
    def __init__(self, start: int, end: int, step: int = 1, type_cast=int):
        self.start = start
        self.end = end
        self.step = step
        self.type_cast = type_cast

    def get_values(self):
        vals = range(self.start, self.end + 1, self.step)
        if self.type_cast == float:
            # Range logic for float if needed, but for now we assume int inputs scaled or just use int params
            pass
        return list(vals)

# Define standard ranges
RSI_PERIODS = [7, 14, 21]
RSI_THRESHOLDS_LOW = [20, 25, 30, 35]
RSI_THRESHOLDS_HIGH = [65, 70, 75, 80]

EMA_FAST_PERIODS = [5, 9, 13, 21]
EMA_SLOW_PERIODS = [21, 34, 55, 89]

SUPERTREND_PERIODS = [7, 10, 14]
SUPERTREND_MULTIPLIERS = [1.5, 2.0, 3.0]

ATR_STOP_MULTIPLIERS = [1.5, 2.0, 3.0, 4.0]
MAX_BARS_HOLD = [5, 10, 20, 50]
