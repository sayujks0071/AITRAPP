import hashlib
import json
import random
from typing import List, Dict, Any
from packages.strategy_foundry.factory.grammar import StrategyType, FilterType, StopType, ParameterSpace

class StrategyGenerator:
    """Generates random strategy specifications"""

    def generate_candidate(self) -> Dict[str, Any]:
        """Generate a single random strategy spec"""

        # 1. Pick Core Strategy
        st_type = random.choice(list(StrategyType))

        spec = {
            "type": st_type.value,
            "params": {},
            "filter": None,
            "stop": None
        }

        # Params
        if st_type == StrategyType.EMA_CROSS:
            spec["params"] = ParameterSpace.get_ema_cross_params()
        elif st_type == StrategyType.RSI_REVERSION:
            spec["params"] = ParameterSpace.get_rsi_reversion_params()
        elif st_type == StrategyType.DONCHIAN_BREAKOUT:
            spec["params"] = ParameterSpace.get_donchian_params()
        elif st_type == StrategyType.SUPERTREND:
            spec["params"] = ParameterSpace.get_supertrend_params()

        # 2. Pick Filter (Optional)
        if random.random() > 0.3: # 70% chance of filter
            ft_type = random.choice([f for f in FilterType if f != FilterType.NONE])
            spec["filter"] = ParameterSpace.get_filter_params(ft_type)

        # 3. Pick Stop (Optional, but recommended)
        if random.random() > 0.1: # 90% chance of stop
            stop_type = random.choice([s for s in StopType])
            spec["stop"] = ParameterSpace.get_stop_params(stop_type)

        # Generate ID
        spec["id"] = self._generate_id(spec)

        return spec

    def _generate_id(self, spec: Dict[str, Any]) -> str:
        """Stable hash of spec"""
        # Create a canonical string representation
        # Sort keys to ensure stability
        s = json.dumps(spec, sort_keys=True)
        return hashlib.md5(s.encode()).hexdigest()[:12]

    def generate_candidates(self, n: int) -> List[Dict[str, Any]]:
        """Generate N unique candidates"""
        candidates = []
        seen_ids = set()

        attempts = 0
        while len(candidates) < n and attempts < n * 10:
            attempts += 1
            cand = self.generate_candidate()
            if cand["id"] not in seen_ids:
                seen_ids.add(cand["id"])
                candidates.append(cand)

        return candidates
