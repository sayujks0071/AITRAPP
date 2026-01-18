from typing import Dict, Any

class ParameterSpace:
    """
    Defines the search space for strategy parameters.
    """

    # Indicator Periods
    RSI_PERIODS = [7, 14, 21]
    ATR_PERIODS = [10, 14, 20]
    ADX_PERIODS = [14, 20]
    SMA_PERIODS = [20, 50, 100, 200]
    EMA_PERIODS = [9, 21, 34, 55, 89]
    BB_PERIODS = [20]
    BB_STD = [2.0, 2.5]
    DONCHIAN_PERIODS = [20, 40, 60]
    SUPERTREND_PERIODS = [10, 14]
    SUPERTREND_MULTIPLIERS = [2.0, 3.0, 4.0]

    # Thresholds
    RSI_OVERBOUGHT = [70, 75, 80]
    RSI_OVERSOLD = [20, 25, 30]
    ADX_THRESHOLD = [20, 25]

    # Risk Management
    STOP_LOSS_ATR_MULT = [1.5, 2.0, 3.0]
    TAKE_PROFIT_ATR_MULT = [2.0, 3.0, 5.0]
    TRAILING_STOP_ATR_MULT = [1.5, 2.0]
    MAX_BARS_HOLD = [12, 24, 48] # e.g., 12*5m = 1 hour, 48*5m = 4 hours

    @classmethod
    def get_random_param(cls, param_name: str) -> Any:
        import random
        if hasattr(cls, param_name):
            return random.choice(getattr(cls, param_name))
        return None
