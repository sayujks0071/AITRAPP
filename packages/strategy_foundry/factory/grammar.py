"""
Strategy grammar and components.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import pandas as pd
import numpy as np
import hashlib
import json
from packages.strategy_foundry.adapters.core_indicators import IndicatorsAdapter

class StrategyComponent(ABC):
    def __init__(self, name: str, params: Dict[str, Any]):
        self.name = name
        self.params = params

    @abstractmethod
    def compute(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.Series:
        """Returns boolean series or float series depending on component type"""
        pass

    def get_id(self) -> str:
        """Stable ID based on name and params"""
        param_str = json.dumps(self.params, sort_keys=True)
        return f"{self.name}:{param_str}"

    def describe(self) -> str:
        param_desc = ", ".join([f"{k}={v}" for k, v in self.params.items()])
        return f"{self.name}({param_desc})"

class EntryRule(StrategyComponent):
    """Returns 1 for Long, -1 for Short, 0 for Neutral"""
    pass

class FilterRule(StrategyComponent):
    """Returns True (1) if allowed, False (0) if not"""
    pass

class ExitRule(StrategyComponent):
    """Returns True if should exit"""
    pass

# --- Implementations ---

class RsiEntry(EntryRule):
    def compute(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.Series:
        # Use specific params from self.params
        calc = IndicatorsAdapter.get_calculator({
            "rsi_period": self.params["period"]
        })
        rsi_series = calc.rsi_series(df)

        lower = self.params["lower"]
        upper = self.params["upper"]

        signals = pd.Series(0, index=df.index)
        signals[rsi_series < lower] = 1
        signals[rsi_series > upper] = -1
        return signals

class EmaCrossEntry(EntryRule):
    def compute(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.Series:
        calc = IndicatorsAdapter.get_calculator({})
        fast = calc.ema_series(df["close"], self.params["fast"])
        slow = calc.ema_series(df["close"], self.params["slow"])

        signals = pd.Series(0, index=df.index)
        signals[fast > slow] = 1
        signals[fast < slow] = -1
        return signals

class SupertrendEntry(EntryRule):
    def compute(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.Series:
        calc = IndicatorsAdapter.get_calculator({
            "supertrend_period": self.params["period"],
            "supertrend_multiplier": self.params["multiplier"]
        })
        # Reuse TR if available, else calc
        tr = indicators.get("tr")
        st, st_dir = calc.supertrend_series(df, tr)
        return pd.Series(st_dir, index=df.index) # st_dir is numpy array, convert to Series

class AdxFilter(FilterRule):
    def compute(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.Series:
        calc = IndicatorsAdapter.get_calculator({
            "adx_period": 14 # Or self.params.get("period", 14)
        })
        tr = indicators.get("tr")
        adx = calc.adx_series(df, tr)
        threshold = self.params["threshold"]
        return adx > threshold

class AtrStop(ExitRule):
    pass

class Strategy:
    def __init__(self, entry_rules: List[EntryRule], filters: List[FilterRule], risk_params: Dict[str, Any]):
        self.entry_rules = entry_rules
        self.filters = filters
        self.risk_params = risk_params
        self.id = self._generate_id()

    def _generate_id(self):
        components = [r.get_id() for r in self.entry_rules] + [f.get_id() for f in self.filters]
        components.append(json.dumps(self.risk_params, sort_keys=True))
        full_str = "|".join(sorted(components))
        return hashlib.md5(full_str.encode()).hexdigest()

    def describe(self) -> str:
        rules = " AND ".join([r.describe() for r in self.entry_rules])
        filters = " AND ".join([f.describe() for f in self.filters])
        return f"Rules: [{rules}] | Filters: [{filters}] | Risk: {self.risk_params}"

    def generate_positions(self, df: pd.DataFrame) -> pd.Series:
        # 1. Compute Shared Indicators (TR, ATR)
        inds = self._compute_shared_indicators(df)

        final_signal = pd.Series(0, index=df.index)

        if not self.entry_rules:
            return final_signal

        # Start with first rule
        combined_signal = self.entry_rules[0].compute(df, inds)

        for rule in self.entry_rules[1:]:
            s = rule.compute(df, inds)
            combined_signal = np.where(combined_signal == s, combined_signal, 0)

        combined_signal = pd.Series(combined_signal, index=df.index)

        # 3. Apply Filters
        for filt in self.filters:
            mask = filt.compute(df, inds)
            combined_signal[~mask] = 0

        return combined_signal

    def apply_risk_overlay(self, df: pd.DataFrame, positions: pd.Series) -> pd.Series:
        return self._apply_stops(df, positions)

    def _compute_shared_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        from packages.strategy_foundry.adapters.core_indicators import IndicatorsAdapter
        calc = IndicatorsAdapter.get_calculator({})

        indicators = {}
        tr = calc.calculate_tr(df)
        indicators["tr"] = tr
        indicators["atr_series"] = calc.atr_series(df, tr) # Default 14 period ATR for Risk overlay
        return indicators

    def _apply_stops(self, df: pd.DataFrame, signals: pd.Series) -> pd.Series:
        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        atr = self._compute_shared_indicators(df)["atr_series"]

        n = len(df)
        final_pos = np.zeros(n)

        current_pos = 0
        entry_price = 0.0
        entry_idx = 0

        atr_mult = self.risk_params.get("atr_stop_mult", 3.0)
        max_bars = self.risk_params.get("max_bars", 50)

        for i in range(1, n):
            target = signals.iloc[i]

            if current_pos != 0:
                stop_dist = atr[entry_idx] * atr_mult
                if current_pos == 1:
                    stop_price = entry_price - stop_dist
                    if low[i] <= stop_price:
                        current_pos = 0
                elif current_pos == -1:
                    stop_price = entry_price + stop_dist
                    if high[i] >= stop_price:
                        current_pos = 0

                if (i - entry_idx) >= max_bars:
                    current_pos = 0

            if current_pos == 0:
                if target != 0:
                    current_pos = target
                    entry_price = close[i]
                    entry_idx = i
            else:
                if (current_pos == 1 and target != 1) or (current_pos == -1 and target != -1):
                     current_pos = 0

            final_pos[i] = current_pos

        return pd.Series(final_pos, index=df.index)
