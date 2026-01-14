from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum

class EntryType(Enum):
    RSI_REVERSION = "rsi_reversion" # Buy if RSI < 30
    RSI_MOMENTUM = "rsi_momentum" # Buy if RSI > 60
    EMA_CROSS = "ema_cross" # Buy if Fast > Slow
    DONCHIAN_BREAKOUT = "donchian_breakout" # Buy if Close > Upper
    SUPERTREND_FOLLOW = "supertrend_follow" # Buy if Supertrend is Bullish
    BB_REVERSION = "bb_reversion" # Buy if Close < Lower Band

class ExitType(Enum):
    ATR_STOP = "atr_stop"
    ATR_TARGET = "atr_target"
    TIME_EXIT = "time_exit"
    SESSION_CLOSE = "session_close" # Mandatory for intraday

@dataclass
class StrategySpec:
    strategy_id: str
    entry_logic: str # EntryType value
    entry_params: Dict[str, Any]

    stop_loss_atr: float
    take_profit_atr: float
    time_exit_bars: Optional[int] = None

    # Intraday constraint
    session_close_time: str = "15:25"

    def to_dict(self):
        return {
            "strategy_id": self.strategy_id,
            "entry_logic": self.entry_logic,
            "entry_params": self.entry_params,
            "stop_loss_atr": self.stop_loss_atr,
            "take_profit_atr": self.take_profit_atr,
            "time_exit_bars": self.time_exit_bars,
            "session_close_time": self.session_close_time
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
