"""
Strategy Grammar
Defines the components and composition rules for strategies.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

@dataclass
class Parameter:
    name: str
    type: str  # int, float, bool, choice
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    options: Optional[List[Any]] = None
    default: Any = None

@dataclass
class Block:
    name: str
    type: str  # entry, exit, filter
    params: Dict[str, Parameter]
    logic: str  # Description of logic

# Registry of available blocks
BLOCKS = {
    # ENTRIES
    "entry_trend_ema_cross": Block(
        name="EMA Crossover",
        type="entry",
        params={
            "fast_period": Parameter("fast_period", "int", 5, 50, 5, default=20),
            "slow_period": Parameter("slow_period", "int", 20, 200, 10, default=50),
            "adx_filter": Parameter("adx_filter", "bool", default=False),
            "adx_threshold": Parameter("adx_threshold", "int", 15, 30, 5, default=20)
        },
        logic="Fast EMA crosses above Slow EMA. Optional ADX > threshold."
    ),
    "entry_breakout_donchian": Block(
        name="Donchian Breakout",
        type="entry",
        params={
            "period": Parameter("period", "int", 10, 60, 5, default=20),
            "filter_ma": Parameter("filter_ma", "bool", default=True),
            "ma_period": Parameter("ma_period", "int", 50, 200, 50, default=200)
        },
        logic="Close > Donchian High(period). Optional Close > SMA(ma_period)."
    ),
    "entry_mean_rev_rsi": Block(
        name="RSI Reversion",
        type="entry",
        params={
            "rsi_period": Parameter("rsi_period", "int", 2, 14, 2, default=7),
            "oversold": Parameter("oversold", "int", 10, 40, 5, default=30),
            "exit_rsi": Parameter("exit_rsi", "int", 50, 80, 5, default=60)
        },
        logic="RSI < oversold. Exit when RSI > exit_rsi (handled as internal exit condition)."
    ),

    # RISKS (Stop Loss / Take Profit)
    "risk_atr": Block(
        name="ATR Stop",
        type="risk",
        params={
            "atr_period": Parameter("atr_period", "int", 14, 14, 1, default=14), # step cannot be 0
            "multiplier": Parameter("multiplier", "float", 1.0, 4.0, 0.5, default=2.0),
            "trailing": Parameter("trailing", "bool", default=False)
        },
        logic="Stop Loss at Entry - (ATR * multiplier). Optional trailing."
    ),

    # EXITS (Target)
    "exit_rr": Block(
        name="Risk Reward Target",
        type="exit",
        params={
            "risk_reward": Parameter("risk_reward", "float", 1.5, 4.0, 0.5, default=2.0)
        },
        logic="Take Profit at Entry + (Risk * RiskReward)."
    ),
    "exit_time": Block(
        name="Time Stop",
        type="exit",
        params={
            "max_bars": Parameter("max_bars", "int", 12, 100, 12, default=36) # ~3-4 hours on 5m
        },
        logic="Exit after N bars."
    )
}

@dataclass
class StrategyConfig:
    entry_block: str
    entry_params: Dict[str, Any]
    risk_block: str
    risk_params: Dict[str, Any]
    exit_block: str
    exit_params: Dict[str, Any]
    id: str = ""

    def get_hash(self):
        import hashlib
        import json
        s = json.dumps(self.__dict__, sort_keys=True)
        return hashlib.md5(s.encode()).hexdigest()
