from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import hashlib
import json
from packages.strategy_foundry.adapters.core_indicators import (
    calculate_ema, calculate_rsi, calculate_adx, calculate_atr,
    calculate_supertrend, calculate_donchian, calculate_bollinger_bands
)

class Strategy:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.id = self._generate_id()
        self.blocks = config.get("blocks", [])

    def _generate_id(self) -> str:
        """Stable hash of the configuration"""
        s = json.dumps(self.config, sort_keys=True)
        return hashlib.sha256(s.encode()).hexdigest()[:12]

    def generate_positions(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate raw entry signals.
        1 = Enter Long
        0 = No Action / Hold
        """
        # Default to neutral
        entries = pd.Series(False, index=df.index)

        # Combine all entry conditions (AND logic)
        first_entry = True

        for block in self.blocks:
            category = block.get("category")
            if category == "entry":
                condition = self._evaluate_entry_block(df, block)
                if first_entry:
                    entries = condition
                    first_entry = False
                else:
                    # Fix: Ensure logic combination is type-safe
                    # Sometimes `condition` or `entries` might be an integer/boolean array
                    # while the other is a pandas object.
                    entries = entries & condition

        # Fill NA with False
        entries = entries.fillna(False).astype(bool)

        # Convert boolean to positions (this is just raw signal, management handles state)
        # But wait, standard interface returns positions in {-1, 0, 1}?
        # The prompt says "generate_positions(df) -> positions in {-1,0,1}"
        # Usually requires state management for exits.

        # Let's change approach:
        # Calculate Entry signal (boolean)
        # Calculate Exit signal (boolean)
        # Iterate to produce positions (vectorized if possible, but stateful with stops is hard to fully vectorize)

        # Hybrid approach:
        # 1. Calculate Entry Signal Series
        # 2. Calculate Static Exit Signal Series (e.g. reverse cross)
        # 3. Apply Risk Overlay (stops) in a loop or vectorised approximation

        return self._apply_execution_logic(df, entries)

    def _evaluate_entry_block(self, df: pd.DataFrame, block: Dict) -> pd.Series:
        btype = block["type"]
        params = block["params"]

        if btype == "ema_cross":
            fast = calculate_ema(df["close"], params["fast"])
            slow = calculate_ema(df["close"], params["slow"])
            # Crossover: fast > slow AND fast.shift < slow.shift
            return (fast > slow) & (fast.shift(1) <= slow.shift(1))

        elif btype == "rsi_reversion":
            rsi = calculate_rsi(df["close"], params["period"])
            return rsi < params["lower_threshold"]

        elif btype == "supertrend_trend":
             st, direction = calculate_supertrend(df, params["period"], params["multiplier"])
             # Enter if direction is 1 (up)
             return direction == 1

        elif btype == "donchian_breakout":
            upper, lower = calculate_donchian(df, params["period"])
            # Close > Upper.shift(1) (breakout of previous high)
            return df["close"] > upper.shift(1)

        elif btype == "adx_filter":
             adx = calculate_adx(df, params["period"])
             return adx > params["threshold"]

        return pd.Series(True, index=df.index)

    def _apply_execution_logic(self, df: pd.DataFrame, entries: pd.Series) -> pd.Series:
        """
        Convert entry signals to positions state {-1, 0, 1}.
        Applies exits and risk management.
        """
        # This implementation uses a loop for correctness with complex stops.
        # For pure vectorization, we'd need simpler logic.
        # Given "Daily" timeframe, a loop is acceptable for speed in backtest.

        positions = np.zeros(len(df))
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        ts = df.index

        # Find risk blocks
        stop_loss_pct = None
        trailing_stop_pct = None
        time_stop = None
        take_profit_pct = None

        for block in self.blocks:
            if block["category"] == "risk":
                if block["type"] == "stop_loss_pct":
                    stop_loss_pct = block["params"]["pct"]
                elif block["type"] == "trailing_stop_pct":
                    trailing_stop_pct = block["params"]["pct"]
                elif block["type"] == "time_stop":
                    time_stop = block["params"]["bars"]
                elif block["type"] == "take_profit_pct":
                    take_profit_pct = block["params"]["pct"]

        # Fallback defaults if no risk block (sanity)
        if stop_loss_pct is None and trailing_stop_pct is None:
             stop_loss_pct = 0.05 # Default 5% stop if nothing specified

        in_trade = False
        entry_price = 0.0
        bars_in_trade = 0
        highest_high = 0.0

        entry_signals = entries.values

        for i in range(1, len(df)):
            # If in trade, check exits
            if in_trade:
                bars_in_trade += 1

                # Check Stops
                exit_signal = False

                # 1. Fixed Stop Loss
                if stop_loss_pct and low[i] < entry_price * (1 - stop_loss_pct):
                    exit_signal = True

                # 2. Trailing Stop
                if trailing_stop_pct:
                    highest_high = max(highest_high, high[i])
                    if low[i] < highest_high * (1 - trailing_stop_pct):
                        exit_signal = True

                # 3. Time Stop
                if time_stop and bars_in_trade >= time_stop:
                    exit_signal = True

                # 4. Take Profit
                if take_profit_pct and high[i] > entry_price * (1 + take_profit_pct):
                    exit_signal = True

                if exit_signal:
                    positions[i] = 0
                    in_trade = False
                else:
                    positions[i] = 1 # Hold

            # If not in trade, check entry
            else: # elif not in_trade: to ensure we don't re-enter same bar
                if entry_signals[i-1]: # Enter on Open of current bar based on signal from previous Close
                    positions[i] = 1
                    in_trade = True
                    entry_price = df["open"].iloc[i] # Approximate entry at Open
                    highest_high = entry_price
                    bars_in_trade = 0

        return pd.Series(positions, index=df.index)

    def rule_summary(self) -> str:
        parts = []
        for block in self.blocks:
            p_str = ",".join([f"{k}={v}" for k,v in block["params"].items()])
            parts.append(f"{block['type']}({p_str})")
        return " + ".join(parts)
