import hashlib
import json
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

@dataclass
class StrategyCandidate:
    """
    A strategy candidate with a fixed DNA (parameters) and a logic engine.
    """
    strategy_id: str
    params: Dict[str, Any]
    source_code: str = "" # Human readable summary

    def to_json(self) -> Dict[str, Any]:
        return {
            "id": self.strategy_id,
            "params": self.params,
            "rule_summary": self.source_code
        }

    @staticmethod
    def from_json(data: Dict[str, Any]) -> 'StrategyCandidate':
        return StrategyCandidate(
            strategy_id=data["id"],
            params=data["params"],
            source_code=data.get("rule_summary", "")
        )

    def generate_positions(self, df: pd.DataFrame, indicators: pd.DataFrame) -> pd.Series:
        """
        Vectorized position generation.
        Returns: Series of {-1, 0, 1} indicating target position.
        """
        p = self.params

        # --- Entry Logic ---
        long_entry = pd.Series(False, index=df.index)
        short_entry = pd.Series(False, index=df.index)

        # 1. Trend Filter
        trend_ok = pd.Series(True, index=df.index)
        if p.get("use_adx_filter"):
            trend_ok &= (indicators["adx"] > p["adx_threshold"])

        if p.get("regime_filter") == "ema_200":
             # If close > ema_slow (assuming slow is roughly 200 or similar proxy)
             # Let's use ema_slow from indicators
             trend_ok &= (df["close"] > indicators["ema_slow"])

        # 2. Entry Triggers
        trigger_type = p.get("entry_type", "supertrend")

        if trigger_type == "supertrend":
            long_entry = (indicators["supertrend_dir"] == 1)
            # Supertrend is continuous, so we want the *change* to 1?
            # Or just "be in long" while 1?
            # Strategy Engine usually takes "Target Position".
            # So if Supertrend is 1, we want to be Long.
            pass

        elif trigger_type == "ema_cross":
            long_entry = (indicators["ema_fast"] > indicators["ema_slow"])

        elif trigger_type == "donchian_breakout":
            # Close > Previous High
            long_entry = (df["close"] > indicators["donchian_upper"].shift(1))

        elif trigger_type == "rsi_reversal":
            # RSI < 30
            long_entry = (indicators["rsi"] < p.get("rsi_lower", 30))

        elif trigger_type == "bb_reversion":
            # Close < Lower Band
            long_entry = (df["close"] < indicators["bb_lower"])

        # Combine
        long_signal = long_entry & trend_ok

        # --- Position State Management ---
        # Since we are outputting a target position series, we can just return the boolean as integer.
        # But we need to handle Exits (Stop Loss / Take Profit) which are path dependent.
        # Pure vectorization of TP/SL is hard without a loop or specialized numbals.
        # For this "Fast Mode", we will output the "Entry Signal" here.
        # The Backtest Engine will handle TP/SL/Trailing logic path-dependently.
        # So we return Entry Signals: 1 (Enter Long), -1 (Enter Short), 0 (Neutral).

        # However, if the strategy is "Always in market" (like Supertrend), the signal is stateful.
        # If it is "Event based" (like RSI < 30), it is an impulse.

        # We will standardize on: Target Position.
        # If trigger_type is persistent (Supertrend, EMA Cross), we return 1 while condition holds.
        # If trigger_type is transient (RSI, Breakout), we return 1 ONLY on the trigger bar?
        # No, for simplicity in the Engine, let's return the "Desired Direction" based on indicators.
        # The Engine will apply Risk Overlay (Stops).

        # Transient to Persistent conversion:
        # If RSI < 30, Enter Long. Hold until RSI > 70?
        # This requires an exit condition.

        # Let's stick to simple "State" indicators for now for the generated strategies.
        # If RSI Reversion: Long when RSI < 30, Neutral when RSI > 50?

        final_signal = pd.Series(0, index=df.index)

        if p.get("direction") == "long_only":
            final_signal[long_signal] = 1
        else:
            # Short logic would go here
            final_signal[long_signal] = 1

        return final_signal

    def get_risk_params(self) -> Dict[str, float]:
        """
        Extract risk parameters for the engine.
        """
        return {
            "stop_loss_pct": self.params.get("stop_loss_pct", 2.0),
            "take_profit_pct": self.params.get("take_profit_pct", 0.0), # 0 means disabled
            "trailing_stop_activation_pct": self.params.get("trailing_stop_activation_pct", 0.0),
            "trailing_stop_callback_pct": self.params.get("trailing_stop_callback_pct", 0.0),
            "max_bars_hold": self.params.get("max_bars_hold", 0)
        }
