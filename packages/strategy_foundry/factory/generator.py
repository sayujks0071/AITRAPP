"""Strategy Generator"""
import random
import hashlib
import json
from typing import List, Dict, Any
from .grammar import Rule, TrendFollowingRule, SupertrendRule, RSIReversionRule, StopLossRule
from .parameter_space import ParameterSpace

class StrategyCandidate:
    def __init__(self, entry_rule: Rule, exit_rule: Rule, stop_loss: StopLossRule):
        self.entry_rule = entry_rule
        self.exit_rule = exit_rule # Can be same as entry (reversal)
        self.stop_loss = stop_loss

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry": self.entry_rule.description(),
            "exit": self.exit_rule.description(),
            "stop": self.stop_loss.description()
        }

    @property
    def id(self) -> str:
        s = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.md5(s.encode()).hexdigest()

    def generate_positions(self, df, indicators):
        # 1. Entry Signal
        entry_sig = self.entry_rule.generate_signal(df, indicators)

        # 2. Apply SL (handled in backtest engine usually, but we can simulate signal cut here if we had state)
        # For vector backtest, we just pass the raw entry signal and let engine handle stops/exits.

        # If exit rule is different, we combine.
        # Simple mode: If entry != 0, take it.
        # If exit != 0, take it (usually 0 to flatten).

        # We return the raw signal series to be processed by engine
        return entry_sig

class StrategyGenerator:
    def __init__(self):
        self.params = ParameterSpace()

    def generate(self, n: int = 10) -> List[StrategyCandidate]:
        candidates = []
        seen = set()

        while len(candidates) < n:
            strat = self._create_random_strategy()
            if strat.id not in seen:
                seen.add(strat.id)
                candidates.append(strat)

        return candidates

    def _create_random_strategy(self) -> StrategyCandidate:
        # Pick strategy type
        type_ = random.choice(["trend_ema", "trend_supertrend", "mean_rsi"])

        if type_ == "trend_ema":
            # Exclude the last element for fast, to ensure slow has options
            fast = random.choice(self.params.EMA_PERIODS[:-1])
            slow = random.choice([p for p in self.params.EMA_PERIODS if p > fast])
            entry = TrendFollowingRule(fast, slow)
            # For trend, exit is usually reverse signal
            exit_rule = entry

        elif type_ == "trend_supertrend":
            per = random.choice(self.params.SUPERTREND_PERIODS)
            mul = random.choice(self.params.SUPERTREND_MULTIPLIERS)
            entry = SupertrendRule(per, mul)
            exit_rule = entry

        else: # mean_rsi
            per = random.choice(self.params.RSI_PERIODS)
            b = random.choice(self.params.RSI_BOUNDS)
            entry = RSIReversionRule(per, b[0], b[1])
            exit_rule = entry # Simple reversal

        # Stop Loss
        atr_p = random.choice(self.params.ATR_PERIODS)
        atr_m = random.choice(self.params.ATR_SL_MULTIPLIERS)
        sl = StopLossRule(atr_p, atr_m)

        return StrategyCandidate(entry, exit_rule, sl)
