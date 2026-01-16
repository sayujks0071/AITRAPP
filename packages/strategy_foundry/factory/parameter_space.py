"""Parameter Space Definitions"""

class ParameterSpace:
    EMA_PERIODS = [9, 21, 34, 55, 89, 144, 200]
    RSI_PERIODS = [7, 14, 21]
    RSI_BOUNDS = [(30, 70), (20, 80), (40, 60)]
    SUPERTREND_PERIODS = [7, 10, 14]
    SUPERTREND_MULTIPLIERS = [1.5, 2.0, 3.0]
    ATR_PERIODS = [14]
    ATR_SL_MULTIPLIERS = [1.0, 1.5, 2.0, 3.0]
