"""
Strategy Generator.
"""
import random
from typing import List
from .grammar import StrategyCandidate, ParameterSpace

class StrategyGenerator:
    """
    Generates random strategies based on the grammar.
    """

    def __init__(self):
        pass

    def generate(self, n: int = 1) -> List[StrategyCandidate]:
        candidates = []
        for _ in range(n):
            candidates.append(self._create_random_strategy())
        return candidates

    def _create_random_strategy(self) -> StrategyCandidate:
        """
        Compose a strategy from blocks.
        """
        # Pick a strategy type/archetype
        archetype = random.choice(["trend_following", "mean_reversion"])

        entry_rules = []
        exit_rules = []
        params = {}

        if archetype == "trend_following":
            # EMA Crossover
            params["ema_fast"] = ParameterSpace.sample("ema_fast")
            params["ema_slow"] = ParameterSpace.sample("ema_slow")
            entry_rules.append({"type": "ema_cross_above", "fast": "ema_fast", "slow": "ema_slow"})
            exit_rules.append({"type": "ema_cross_below", "fast": "ema_fast", "slow": "ema_slow"})

            # Optional Filter: ADX or Regime
            if random.random() < 0.5:
                 # Supertrend filter
                 params["supertrend_period"] = ParameterSpace.sample("supertrend_period")
                 params["supertrend_multiplier"] = ParameterSpace.sample("supertrend_multiplier")
                 entry_rules.append({"type": "supertrend_bullish"})

        elif archetype == "mean_reversion":
            # RSI Reversion
            params["rsi_period"] = ParameterSpace.sample("rsi_period")
            params["rsi_buy"] = ParameterSpace.sample("rsi_buy_threshold")
            params["rsi_sell"] = ParameterSpace.sample("rsi_sell_threshold")

            entry_rules.append({"type": "rsi_oversold", "period": "rsi_period", "threshold": "rsi_buy"})
            exit_rules.append({"type": "rsi_overbought", "period": "rsi_period", "threshold": "rsi_sell"})

            # Optional: Bollinger Bands
            if random.random() < 0.3:
                 params["bb_period"] = ParameterSpace.sample("bb_period")
                 params["bb_std"] = ParameterSpace.sample("bb_std")
                 entry_rules.append({"type": "price_below_bb_lower"})

        # Common Risk Management (Stop Loss)
        params["atr_period"] = ParameterSpace.sample("atr_period")
        params["stop_loss_atr"] = ParameterSpace.sample("stop_loss_atr")
        exit_rules.append({"type": "trailing_stop_atr", "multiplier": "stop_loss_atr"})

        # Time Stop
        if random.random() < 0.5:
             params["max_bars_hold"] = ParameterSpace.sample("max_bars_hold")
             exit_rules.append({"type": "time_stop", "bars": "max_bars_hold"})

        candidate = StrategyCandidate(
            id="",
            entry_rules=entry_rules,
            exit_rules=exit_rules,
            params=params
        )
        candidate.id = candidate.generate_id()
        return candidate
