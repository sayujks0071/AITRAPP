import random
import hashlib
import pandas as pd
from typing import List, Dict, Any
from packages.strategy_foundry.factory.grammar import StrategyCandidate, Rule

# --- Rule Implementations ---

def rule_ema_cross(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    fast = params["fast"]
    slow = params["slow"]
    # Dynamic column lookup based on params available in VectorizedIndicators
    # We generated ema_10, ema_20, ema_50, ema_200
    # If param requests something else, we might fail or default.
    # To be safe, we only allow specific periods in params generation.
    col_fast = f"ema_{fast}"
    col_slow = f"ema_{slow}"
    if col_fast in df.columns and col_slow in df.columns:
        return df[col_fast] > df[col_slow]
    return pd.Series(False, index=df.index)

def rule_supertrend_long(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    # Supertrend direction 1 is usually UP (Bullish)
    return df["supertrend_dir"] == 1

def rule_rsi_entry(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    thresh = params["threshold"]
    return df["rsi_14"] < thresh

def rule_rsi_exit(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    thresh = params["threshold"]
    return df["rsi_14"] > thresh

def rule_adx_filter(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    thresh = params["threshold"]
    return df["adx_14"] > thresh

def rule_regime_filter(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    # Close > SMA 200 (Long term trend)
    # We didn't compute sma_200 in adapter, let's check.
    # We computed ema_200. Let's use ema_200 for regime.
    return df["close"] > df["ema_200"]

def rule_donchian_breakout(df: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
    # Close > Upper previous (breakout)
    # Actually Donchian Upper is max of high, so close >= Upper means breakout
    return df["close"] >= df["dc_upper"].shift(1)

# --- Generator ---

class StrategyGenerator:
    def __init__(self):
        self.ema_periods = [10, 20, 50, 200]
        self.rsi_thresholds_entry = [20, 25, 30, 35, 40]
        self.rsi_thresholds_exit = [60, 65, 70, 75, 80]
        self.adx_thresholds = [20, 25, 30]

    def generate_random_strategy(self) -> StrategyCandidate:
        entry_rules = []
        exit_rules = []

        # Pick a base logic type
        logic_type = random.choice(["TREND", "MEAN_REV", "BREAKOUT"])

        if logic_type == "TREND":
            # EMA Cross or Supertrend
            if random.random() < 0.5:
                p1, p2 = sorted(random.sample([10, 20, 50, 200], 2))
                entry_rules.append(Rule("EMA_Cross", rule_ema_cross, {"fast": p1, "slow": p2}))
            else:
                entry_rules.append(Rule("Supertrend_Bull", rule_supertrend_long, {}))

            # Add ADX Filter
            if random.random() < 0.5:
                t = random.choice(self.adx_thresholds)
                entry_rules.append(Rule("ADX_Filter", rule_adx_filter, {"threshold": t}))

        elif logic_type == "MEAN_REV":
            # RSI Entry
            t = random.choice(self.rsi_thresholds_entry)
            entry_rules.append(Rule("RSI_Oversold", rule_rsi_entry, {"threshold": t}))

            # Regime filter (only buy dips in uptrend)
            if random.random() < 0.7:
                entry_rules.append(Rule("Regime_Filter", rule_regime_filter, {}))

            # RSI Exit
            t_exit = random.choice(self.rsi_thresholds_exit)
            exit_rules.append(Rule("RSI_Overbought", rule_rsi_exit, {"threshold": t_exit}))

        elif logic_type == "BREAKOUT":
            entry_rules.append(Rule("Donchian_Breakout", rule_donchian_breakout, {}))
            # Usually needs volatility filter
            if random.random() < 0.5:
                 t = random.choice(self.adx_thresholds)
                 entry_rules.append(Rule("ADX_Filter", rule_adx_filter, {"threshold": t}))

        # Risk Params
        risk = {
            "sl_atr": round(random.uniform(1.5, 4.0), 1),
            "tp_atr": round(random.choice([0, random.uniform(2.0, 6.0)]), 1),
            "max_bars": random.choice([0, 5, 10, 20]),
            "trailing_sl": random.choice([True, False])
        }

        # ID generation
        summary = f"{logic_type}|" + "|".join([r.name + str(r.params) for r in entry_rules]) + "|" + str(risk)
        strat_id = hashlib.md5(summary.encode()).hexdigest()[:12]

        return StrategyCandidate(
            strategy_id=strat_id,
            entry_rules=entry_rules,
            exit_rules=exit_rules,
            risk_params=risk
        )

    def generate_candidates(self, n: int) -> List[StrategyCandidate]:
        candidates = []
        seen = set()
        attempts = 0
        while len(candidates) < n and attempts < n * 5:
            strat = self.generate_random_strategy()
            if strat.strategy_id not in seen:
                candidates.append(strat)
                seen.add(strat.strategy_id)
            attempts += 1
        return candidates
