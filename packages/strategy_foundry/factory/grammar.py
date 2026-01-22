import hashlib
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from packages.strategy_foundry.adapters.core_indicators import IndicatorsAdapter

class Strategy:
    """
    Represents a trading strategy composed of blocks.
    """

    def __init__(self, entry_blocks: List[Dict], exit_blocks: List[Dict], filters: List[Dict]):
        self.entry_blocks = entry_blocks
        self.exit_blocks = exit_blocks
        self.filters = filters
        self.id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate unique ID based on rules."""
        spec = {
            "entry": self.entry_blocks,
            "exit": self.exit_blocks,
            "filters": self.filters
        }
        s = json.dumps(spec, sort_keys=True)
        return hashlib.sha256(s.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "entry_blocks": self.entry_blocks,
            "exit_blocks": self.exit_blocks,
            "filters": self.filters
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(data["entry_blocks"], data["exit_blocks"], data["filters"])

    def calculate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate signals: 1 (Long), -1 (Short), 0 (Flat/Exit).
        For simplicity in this foundry, we might just return "Target Position" or "Entry Signal".
        Let's return an integer series where:
          1 = Entry Long
         -1 = Entry Short (if enabled, default 0 for now)
          0 = No Entry (or Exit if held)

        Actually, a better model for the backtester is:
        return `entries` (1/0/-1) and `exits` (True/False).
        """
        # Calculate Indicators dynamically
        # We'll calculate columns and add to a local DF copy or dict of series

        entries = pd.Series(0, index=df.index)
        exits = pd.Series(False, index=df.index)

        # 1. Filters
        # If any filter is False, no entry
        # We can implement filters as a boolean mask
        trade_allowed = pd.Series(True, index=df.index)

        for f in self.filters:
            ftype = f["type"]
            params = f["params"]

            if ftype == "trend_filter_ema":
                ema = IndicatorsAdapter.calculate_indicator(df, "ema_slow", {"ema_slow": params["period"]})
                # Only long if Price > EMA
                trade_allowed &= (df["close"] > ema)
            # Add more filters here

        # 2. Entries
        # If any entry block triggers, we signal entry
        # Usually we OR them, or we just have one entry block per strategy for simplicity
        entry_signal = pd.Series(0, index=df.index)

        for block in self.entry_blocks:
            btype = block["type"]
            params = block["params"]

            if btype == "rsi_reversion":
                rsi = IndicatorsAdapter.calculate_indicator(df, "rsi", params)
                # Long if RSI < lower
                # Short if RSI > upper (if we did short)
                entry_signal = np.where(rsi < params["lower"], 1, entry_signal)

            elif btype == "bollinger_reversion":
                # Close below lower band
                bb = IndicatorsAdapter.get_calculator({"bb_period": params["period"], "bb_std": params["std"]})
                u, m, l = bb.bollinger_bands_series(df["close"])
                entry_signal = np.where(df["close"] < l, 1, entry_signal)

            elif btype == "ema_crossover":
                fast = IndicatorsAdapter.calculate_indicator(df, "ema_fast", {"ema_fast": params["fast"]})
                slow = IndicatorsAdapter.calculate_indicator(df, "ema_slow", {"ema_slow": params["slow"]})
                # Cross over
                # This logic checks condition state. For true crossover we need prev state.
                # But let's say we are in "Trend" mode: Fast > Slow.
                # Or specific crossover: Fast > Slow AND Fast[i-1] <= Slow[i-1]
                # Using vectorized approach for crossover is tricky without shift
                cond = (fast > slow)
                prev_cond = cond.shift(1).fillna(False)
                crossover = cond & (~prev_cond)
                entry_signal = np.where(crossover, 1, entry_signal)

            elif btype == "donchian_breakout":
                calc = IndicatorsAdapter.get_calculator({"donchian_period": params["period"]})
                u, l = calc.donchian_series(df, period=params["period"])
                # Breakout: High > Prev Upper (Donchian is usually shifted by 1 for signal, but here `u` includes current)
                # If we use High > u.shift(1)
                prev_u = u.shift(1)
                entry_signal = np.where(df["high"] > prev_u, 1, entry_signal)

            elif btype == "orb_breakout":
                # Only valid after window
                # Get Day High/Low of first X mins
                # This is hard to vectorize efficiently without resampling.
                # We can skip for now or do a simple approximation if needed.
                # Or reuse `packages.core.strategies.orb` if we could, but that's a full strategy class.
                # Let's implement a simplified ORB logic:
                # Calculate intraday cumulative high/low up to window, then extend.
                pass

        entries = np.where(trade_allowed, entry_signal, 0)

        # 3. Exits (Logical)
        # These are conditions that force an exit if we are in a position
        # Note: Backtester handles Stops/TakeProfits separately usually.
        # These are "Signal" exits (e.g. RSI crossed back).

        # We return a mask of "Exit Now"
        exit_signal = pd.Series(False, index=df.index)

        for block in self.exit_blocks:
            btype = block["type"]
            params = block["params"]

            if btype == "rsi_exit":
                rsi = IndicatorsAdapter.calculate_indicator(df, "rsi", params)
                exit_signal |= (rsi > params["threshold"])

            # Time stop is handled by backtester usually, but if we wanted to enforce it here
            # we'd need to know entry time, which we don't. So TimeStop is a "Risk" rule, not "Signal" rule.

        return pd.Series(entries, index=df.index), exit_signal

    def get_risk_params(self) -> Dict:
        """Extract risk parameters for the backtester (stops, etc)."""
        params = {}
        for b in self.exit_blocks:
            if b["type"] == "time_stop":
                params["time_stop_bars"] = b["params"]["bars"]
            elif b["type"] == "trailing_stop_atr":
                params["trailing_stop_atr"] = b["params"]
        return params
