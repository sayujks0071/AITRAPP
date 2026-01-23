from typing import List
import random
from packages.strategy_foundry.factory.grammar import Strategy
from packages.strategy_foundry.factory.parameter_space import ParameterSpace

class StrategyGenerator:
    """
    Generates random strategies.
    """

    @staticmethod
    def generate_random() -> Strategy:
        # 1. Entry Block (Always 1 for MVP)
        entry_type = ParameterSpace.sample_entry_type()
        entry_block = {
            "type": entry_type,
            "params": ParameterSpace.get_params(entry_type)
        }

        # 2. Exit/Risk Blocks
        exit_blocks = []

        # Chance to add Time Stop
        if random.random() < 0.7:
            exit_blocks.append({
                "type": "time_stop",
                "params": ParameterSpace.get_params("time_stop")
            })

        # Chance to add Trailing Stop or Signal Exit
        other_exit = random.choice(["trailing_stop_atr", "rsi_exit", None])
        if other_exit:
            exit_blocks.append({
                "type": other_exit,
                "params": ParameterSpace.get_params(other_exit)
            })

        # Ensure at least one exit/risk control if none selected (unlikely but safe)
        if not exit_blocks:
             exit_blocks.append({
                "type": "time_stop",
                "params": ParameterSpace.get_params("time_stop")
            })

        # 3. Filters
        filters = []
        if random.random() < 0.5:
            filter_type = ParameterSpace.sample_filter_type()
            if filter_type != "no_filter":
                filters.append({
                    "type": filter_type,
                    "params": ParameterSpace.get_params(filter_type)
                })

        return Strategy(
            entry_blocks=[entry_block],
            exit_blocks=exit_blocks,
            filters=filters
        )

    @staticmethod
    def generate_population(n: int) -> List[Strategy]:
        strategies = []
        seen_ids = set()

        attempts = 0
        while len(strategies) < n and attempts < n * 10:
            s = StrategyGenerator.generate_random()
            if s.id not in seen_ids:
                strategies.append(s)
                seen_ids.add(s.id)
            attempts += 1

        return strategies
