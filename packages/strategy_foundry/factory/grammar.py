from dataclasses import dataclass, field
from typing import List, Callable, Dict, Any, Optional
import pandas as pd
import hashlib
import json
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class Rule:
    name: str
    func: Callable[[pd.DataFrame, Dict[str, Any]], pd.Series]
    params: Dict[str, Any]

    def apply(self, df: pd.DataFrame) -> pd.Series:
        return self.func(df, self.params)

    def to_dict(self):
        return {"name": self.name, "params": self.params}

@dataclass
class StrategyCandidate:
    strategy_id: str
    entry_rules: List[Rule]
    exit_rules: List[Rule]
    risk_params: Dict[str, Any]

    def generate_raw_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate raw signals.
        1 = Enter Long
        -10 = Exit Long
        0 = Neutral
        """
        # Entry Signal (AND logic)
        if not self.entry_rules:
            entry_signal = pd.Series(False, index=df.index)
        else:
            entry_signal = pd.Series(True, index=df.index)
            for rule in self.entry_rules:
                entry_signal &= rule.apply(df)

        # Exit Signal (OR logic)
        exit_signal = pd.Series(False, index=df.index)
        for rule in self.exit_rules:
            exit_signal |= rule.apply(df)

        signals = pd.Series(0, index=df.index)
        signals[entry_signal] = 1
        signals[exit_signal] = -10 # Exit overrides entry

        return signals

    def generate_positions(self, df: pd.DataFrame) -> pd.Series:
        """
        Standard interface wrapper. Returns final positions after risk overlay.
        """
        raw = self.generate_raw_signals(df)
        return self.apply_risk_overlay(df, raw)

    def apply_risk_overlay(self, df: pd.DataFrame, raw_signals: pd.Series) -> pd.Series:
        """
        Apply stops and risk management to generate final positions.
        Simulates Next-Bar-Open execution for entries.
        """
        final_positions = pd.Series(0, index=df.index)
        entry_idx = 0
        stop_loss = 0.0
        take_profit = 0.0

        atr = df["atr_14"] if "atr_14" in df else df["atr"]

        # Params
        sl_mult = self.risk_params.get("sl_atr", 2.0)
        tp_mult = self.risk_params.get("tp_atr", 0.0)
        max_bars = self.risk_params.get("max_bars", 0)
        trailing_sl = self.risk_params.get("trailing_sl", False)

        closes = df["close"].values
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        atrs = atr.values
        sigs = raw_signals.values

        current_pos = 0 # 0 or 1

        pending_entry = False
        pending_sl = 0.0
        pending_tp = 0.0

        # Start from 1 as we need history (and we use pending logic)
        for i in range(1, len(df)):

            # 1. Process Pending Entry (Execute at Open)
            if pending_entry:
                current_pos = 1
                entry_idx = i
                stop_loss = pending_sl
                take_profit = pending_tp
                pending_entry = False

            # 2. Manage Trade (Exits)
            if current_pos == 1:
                # Check intraday exits against High/Low

                # Stop Loss
                if lows[i] <= stop_loss:
                    current_pos = 0
                # Take Profit
                elif tp_mult > 0 and highs[i] >= take_profit:
                    current_pos = 0
                # Time Stop
                elif max_bars > 0 and (i - entry_idx) >= max_bars:
                    current_pos = 0

                # Technical Exit (Signal from previous bar meant exit at Open,
                # OR Signal at current bar means exit at Close?)
                # If we assume sigs[i] == -10 is an exit signal generated at Close[i],
                # we should exit at Open[i+1].
                # But here we are simplifying to "Exit Logic".
                # For the vector, let's assume exit at Close if signal present.
                elif sigs[i] == -10:
                    current_pos = 0

                # Update Trailing Stop (for NEXT bar)
                if current_pos == 1 and trailing_sl:
                    new_sl = closes[i] - atrs[i] * sl_mult
                    if new_sl > stop_loss:
                        stop_loss = new_sl

            # 3. Check New Entry Signal (if flat and no pending entry)
            if current_pos == 0 and not pending_entry:
                if sigs[i] == 1:
                    pending_entry = True
                    # Calc stops based on Close[i]
                    ref_price = closes[i]
                    ref_atr = atrs[i]
                    pending_sl = ref_price - ref_atr * sl_mult
                    if tp_mult > 0:
                        pending_tp = ref_price + ref_atr * tp_mult
                    else:
                        pending_tp = 0

            final_positions.iloc[i] = current_pos

        return final_positions

    def get_summary(self) -> str:
        entries = " AND ".join([f"{r.name}({r.params})" for r in self.entry_rules])
        exits = " OR ".join([f"{r.name}({r.params})" for r in self.exit_rules])
        return f"Entry: [{entries}] | Exit: [{exits}] | Risk: {self.risk_params}"

    def to_json(self):
        return {
            "id": self.strategy_id,
            "entry": [r.to_dict() for r in self.entry_rules],
            "exit": [r.to_dict() for r in self.exit_rules],
            "risk": self.risk_params
        }
