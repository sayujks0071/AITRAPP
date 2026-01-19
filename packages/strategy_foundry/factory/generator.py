"""
Strategy generator.
"""
import random
from typing import List
from packages.strategy_foundry.factory.grammar import (
    Strategy, EmaCrossEntry, RsiEntry, SupertrendEntry, AdxFilter, StrategyComponent
)
from packages.strategy_foundry.factory.parameter_space import (
    RSI_PERIODS, RSI_THRESHOLDS_LOW, RSI_THRESHOLDS_HIGH,
    EMA_FAST_PERIODS, EMA_SLOW_PERIODS,
    SUPERTREND_PERIODS, SUPERTREND_MULTIPLIERS,
    ATR_STOP_MULTIPLIERS, MAX_BARS_HOLD
)

class StrategyGenerator:
    def __init__(self):
        pass

    def generate_candidate(self) -> Strategy:
        # 1. Select Entry Logic (1 component for now)
        entry_type = random.choice(["EMA_CROSS", "RSI", "SUPERTREND"])
        entry_rules = []

        if entry_type == "EMA_CROSS":
            entry_rules.append(EmaCrossEntry("EmaCross", {
                "fast": random.choice(EMA_FAST_PERIODS),
                "slow": random.choice(EMA_SLOW_PERIODS)
            }))
        elif entry_type == "RSI":
            entry_rules.append(RsiEntry("RsiMeanRev", {
                "period": random.choice(RSI_PERIODS),
                "lower": random.choice(RSI_THRESHOLDS_LOW),
                "upper": random.choice(RSI_THRESHOLDS_HIGH)
            }))
        elif entry_type == "SUPERTREND":
            entry_rules.append(SupertrendEntry("SupertrendTrend", {
                "period": random.choice(SUPERTREND_PERIODS),
                "multiplier": random.choice(SUPERTREND_MULTIPLIERS)
            }))

        # 2. Select Filters (0-1)
        filters = []
        if random.random() < 0.3: # 30% chance
            filters.append(AdxFilter("AdxFilter", {
                "period": 14,
                "threshold": 20
            }))

        # 3. Select Risk Params
        risk_params = {
            "atr_stop_mult": random.choice(ATR_STOP_MULTIPLIERS),
            "max_bars": random.choice(MAX_BARS_HOLD)
        }

        return Strategy(entry_rules, filters, risk_params)
