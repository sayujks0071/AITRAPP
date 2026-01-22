# Strategy Foundry
import hashlib
import json
import random
from typing import List

from packages.strategy_foundry.factory.grammar import (
    ExitType,
    FilterType,
    StrategySpec,
    StrategyType,
)
from packages.strategy_foundry.factory.parameter_space import ParameterSpace


class StrategyGenerator:
    def __init__(self):
        pass

    def generate_candidates(self, n: int = 10) -> List[StrategySpec]:
        candidates = []
        hashes = set()

        attempts = 0
        while len(candidates) < n and attempts < n * 5:
            attempts += 1
            spec = self._generate_single()
            spec_id = self._compute_hash(spec)

            if spec_id not in hashes:
                spec["id"] = spec_id
                candidates.append(spec)
                hashes.add(spec_id)

        return candidates

    def _generate_single(self) -> StrategySpec:
        st_type = random.choice(list(StrategyType))
        st_params = {}

        if st_type == StrategyType.BREAKOUT_DONCHIAN:
            st_params["period"] = ParameterSpace.get_random_param("DONCHIAN_PERIODS")

        elif st_type == StrategyType.TREND_EMA_CROSS:
            # fast < slow
            # Ensure fast is not the largest available period
            available_fast = [p for p in ParameterSpace.EMA_PERIODS if p < max(ParameterSpace.EMA_PERIODS)]
            fast = random.choice(available_fast)

            available_slow = [p for p in ParameterSpace.EMA_PERIODS if p > fast]
            slow = random.choice(available_slow)

            st_params["fast_period"] = fast
            st_params["slow_period"] = slow

        elif st_type == StrategyType.MEAN_REV_RSI:
            st_params["period"] = ParameterSpace.get_random_param("RSI_PERIODS")
            st_params["oversold"] = ParameterSpace.get_random_param("RSI_OVERSOLD")
            st_params["overbought"] = ParameterSpace.get_random_param("RSI_OVERBOUGHT")

        elif st_type == StrategyType.MEAN_REV_BB:
            st_params["period"] = ParameterSpace.get_random_param("BB_PERIODS")
            st_params["std"] = ParameterSpace.get_random_param("BB_STD")

        elif st_type == StrategyType.VOL_EXPANSION_ATR:
            st_params["period"] = ParameterSpace.get_random_param("ATR_PERIODS")

        elif st_type == StrategyType.SUPERTREND_FOLLOW:
            st_params["period"] = ParameterSpace.get_random_param("SUPERTREND_PERIODS")
            st_params["multiplier"] = ParameterSpace.get_random_param("SUPERTREND_MULTIPLIERS")

        # Filters
        ft_type = random.choice(list(FilterType))
        ft_params = {}
        if ft_type == FilterType.REGIME_EMA:
            ft_params["period"] = ParameterSpace.get_random_param("SMA_PERIODS")
        elif ft_type == FilterType.VOLATILITY_ADX:
            ft_params["period"] = ParameterSpace.get_random_param("ADX_PERIODS")
            ft_params["threshold"] = ParameterSpace.get_random_param("ADX_THRESHOLD")
        elif ft_type == FilterType.RSI_FILTER:
             ft_params["period"] = ParameterSpace.get_random_param("RSI_PERIODS")
             ft_params["max_val"] = 70 # Hardcoded simple filter for long

        # Exits
        ex_type = random.choice(list(ExitType))
        ex_params = {}
        ex_params["sl_mult"] = ParameterSpace.get_random_param("STOP_LOSS_ATR_MULT")
        ex_params["tp_mult"] = ParameterSpace.get_random_param("TAKE_PROFIT_ATR_MULT")

        if ex_type == ExitType.TIME_BASED:
            ex_params["max_bars"] = ParameterSpace.get_random_param("MAX_BARS_HOLD")

        # Mandatory intraday close
        session_close = "15:25"

        return {
            "id": "", # Set later
            "direction": "LONG", # Default Long-only
            "strategy_type": st_type.value,
            "strategy_params": st_params,
            "filter_type": ft_type.value,
            "filter_params": ft_params,
            "exit_type": ex_type.value,
            "exit_params": ex_params,
            "session_close_time": session_close
        }

    def _compute_hash(self, spec: StrategySpec) -> str:
        # Create a deterministic string representation
        # Exclude ID if present
        s = spec.copy()
        if "id" in s:
            del s["id"]

        # Sort keys for stable JSON
        s_str = json.dumps(s, sort_keys=True)
        return hashlib.sha256(s_str.encode("utf-8")).hexdigest()[:16]
