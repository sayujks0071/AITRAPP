from enum import Enum
from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel

class EntryType(str, Enum):
    BREAKOUT = "BREAKOUT"
    TREND = "TREND"
    MEAN_REVERSION = "MEAN_REVERSION"

class RiskType(str, Enum):
    ATR_STOP = "ATR_STOP"
    TIME_STOP = "TIME_STOP"

class FilterType(str, Enum):
    REGIME_MA = "REGIME_MA"
    VOLATILITY = "VOLATILITY"
    TIME_OF_DAY = "TIME_OF_DAY"

class Parameter(BaseModel):
    name: str
    value: Union[int, float, str]

class StrategyComponent(BaseModel):
    type: str
    params: Dict[str, Any]

class StrategyCandidate(BaseModel):
    id: str
    entry: StrategyComponent
    exit: StrategyComponent
    filters: List[StrategyComponent] = []

    # Metadata
    generation_ts: float
    grammar_version: str = "1.0"

    def get_summary(self) -> str:
        f_str = ", ".join([f"{f.type}" for f in self.filters])
        return f"{self.entry.type} + {self.exit.type} [Filters: {f_str}]"
