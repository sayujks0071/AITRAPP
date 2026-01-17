import random
import hashlib
import json
from typing import List
from packages.strategy_foundry.factory.grammar import StrategyCandidate, StrategyRule, Condition, IndicatorDef, Operator
from packages.strategy_foundry.factory.parameter_space import ParameterSpace

class StrategyGenerator:
    """
    Generates random strategies based on the defined grammar and parameter space.
    """

    def generate_candidates(self, count: int, timeframe: str) -> List[StrategyCandidate]:
        candidates = []
        seen_ids = set()

        while len(candidates) < count:
            strategy = self._generate_single_strategy()
            strat_id = self._generate_id(strategy, timeframe)

            if strat_id not in seen_ids:
                seen_ids.add(strat_id)
                candidates.append(StrategyCandidate(
                    id=strat_id,
                    rule=strategy,
                    timeframe=timeframe,
                    source_code=self._to_string(strategy)
                ))

        return candidates

    def _generate_single_strategy(self) -> StrategyRule:
        entry_type = random.choice(ParameterSpace.ENTRY_TYPES)

        if entry_type == "trend_following":
            entry_conds = self._gen_trend_following()
        elif entry_type == "mean_reversion":
            entry_conds = self._gen_mean_reversion()
        else: # breakout
            entry_conds = self._gen_breakout()

        # Add a filter sometimes
        if random.random() < 0.5:
            entry_conds.append(self._gen_filter())

        # Exits are usually standard risk based, but maybe an indicator exit too
        exit_conds = []
        # For now, relying on Risk Params for main exit, and EOD.
        # Maybe add a reversal exit?

        risk = {
            "sl_atr": random.choice(ParameterSpace.RISK_MODELS["stop_loss_atr"]),
            "tp_atr": random.choice(ParameterSpace.RISK_MODELS["take_profit_atr"]),
            "trailing": random.choice(ParameterSpace.RISK_MODELS["trailing_stop"])
        }

        return StrategyRule(
            entry_conditions=entry_conds,
            exit_conditions=exit_conds,
            risk_params=risk,
            description=f"{entry_type} strategy"
        )

    def _gen_trend_following(self) -> List[Condition]:
        # Example: EMA crossover
        fast = random.choice([5, 10, 20])
        slow = random.choice([20, 50, 100])
        if fast >= slow: fast, slow = 10, 50

        c1 = Condition(
            indicator_a=IndicatorDef("ema", {"period": fast}),
            operator=Operator.GT,
            indicator_b=IndicatorDef("ema", {"period": slow})
        )
        return [c1]

    def _gen_mean_reversion(self) -> List[Condition]:
        # Example: RSI < 30
        period = 14
        thresh = random.choice([30, 40])

        c1 = Condition(
            indicator_a=IndicatorDef("rsi", {"period": period}),
            operator=Operator.LT,
            indicator_b=thresh
        )
        return [c1]

    def _gen_breakout(self) -> List[Condition]:
        # Example: Close > Donchian Upper
        period = random.choice([20, 50])

        c1 = Condition(
            indicator_a=IndicatorDef("close", {}),
            operator=Operator.GT,
            indicator_b=IndicatorDef("donchian_upper", {"period": period})
        )
        return [c1]

    def _gen_filter(self) -> Condition:
        # Example: ADX > 20
        return Condition(
            indicator_a=IndicatorDef("adx", {"period": 14}),
            operator=Operator.GT,
            indicator_b=20
        )

    def _generate_id(self, rule: StrategyRule, timeframe: str) -> str:
        # Stable ID based on rule definition
        s = json.dumps(self._rule_to_dict(rule), sort_keys=True) + timeframe
        return hashlib.md5(s.encode()).hexdigest()[:12]

    def _rule_to_dict(self, rule: StrategyRule) -> dict:
        # simplified serialization for hashing
        return {
            "entry": [str(c) for c in rule.entry_conditions],
            "risk": rule.risk_params
        }

    def _to_string(self, rule: StrategyRule) -> str:
        return f"{rule.description} | Risk: {rule.risk_params}"
