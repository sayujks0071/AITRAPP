"""Strategy Grammar and Components"""
from enum import Enum
from typing import Dict, Any, List
from dataclasses import dataclass

class StrategyType(str, Enum):
    LONG_ONLY = "long_only"
    # Short optional, default false per prompt

class EntryType(str, Enum):
    # Breakout
    ORB_BREAKOUT = "orb_breakout" # Opening Range Breakout
    DONCHIAN_BREAKOUT = "donchian_breakout"

    # Trend
    EMA_CROSS = "ema_cross"
    SUPERTREND = "supertrend"

    # Mean Reversion
    RSI_OVERSOLD = "rsi_oversold"
    BOLLINGER_REVERSION = "bollinger_reversion"

class FilterType(str, Enum):
    REGIME_SMA = "regime_sma" # Price > SMA(200)
    ADX_FILTER = "adx_filter" # ADX > threshold
    VOLATILITY_ATR = "volatility_atr" # ATR percentile

class ExitType(str, Enum):
    STOP_LOSS_ATR = "stop_loss_atr"
    TAKE_PROFIT_FIXED = "take_profit_fixed"
    TIME_STOP = "time_stop"
    SESSION_CLOSE = "session_close" # Mandatory

@dataclass
class StrategyCandidate:
    id: str
    source_grammar: str
    entry_block: Dict[str, Any]
    filter_blocks: List[Dict[str, Any]]
    exit_blocks: List[Dict[str, Any]]

    def to_dict(self):
        return {
            "id": self.id,
            "source_grammar": self.source_grammar,
            "entry": self.entry_block,
            "filters": self.filter_blocks,
            "exits": self.exit_blocks
        }
