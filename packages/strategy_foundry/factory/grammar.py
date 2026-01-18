from enum import Enum
from typing import TypedDict, Dict, Any, Optional

class StrategyType(Enum):
    BREAKOUT_DONCHIAN = "BREAKOUT_DONCHIAN"
    TREND_EMA_CROSS = "TREND_EMA_CROSS"
    MEAN_REV_RSI = "MEAN_REV_RSI"
    MEAN_REV_BB = "MEAN_REV_BB"
    VOL_EXPANSION_ATR = "VOL_EXPANSION_ATR"
    SUPERTREND_FOLLOW = "SUPERTREND_FOLLOW"

class FilterType(Enum):
    NO_FILTER = "NO_FILTER"
    REGIME_EMA = "REGIME_EMA" # Close > EMA(200)
    VOLATILITY_ADX = "VOLATILITY_ADX" # ADX > 20
    RSI_FILTER = "RSI_FILTER" # RSI < 70 for Long

class ExitType(Enum):
    FIXED_RR = "FIXED_RR" # SL and TP based on ATR
    TRAILING_ATR = "TRAILING_ATR" # Trailing stop
    TIME_BASED = "TIME_BASED" # Exit after N bars

class StrategySpec(TypedDict):
    id: str
    direction: str # LONG or SHORT (default LONG)

    # Entry Logic
    strategy_type: str
    strategy_params: Dict[str, Any]

    # Filter Logic
    filter_type: str
    filter_params: Dict[str, Any]

    # Exit Logic
    exit_type: str
    exit_params: Dict[str, Any]

    # Global Constraints
    session_close_time: str # "15:25"
