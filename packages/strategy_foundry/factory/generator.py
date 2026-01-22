from typing import List
from packages.strategy_foundry.factory.grammar import Strategy
from packages.strategy_foundry.factory.parameter_space import ParameterSpace

class StrategyGenerator:
    """
    Generates random strategies.
    """

    @staticmethod
    def generate_random() -> Strategy:
        # 1 Entry Block
        entry_type = ParameterSpace.sample_entry_type()
        entry_block = {
            "type": entry_type,
            "params": ParameterSpace.get_params(entry_type)
        }

        # 1-2 Exit Blocks
        exit_blocks = []
        # Always add time stop? Or maybe it's random.
        if ParameterSpace.sample_exit_type() == "time_stop": # explicit sample
             exit_blocks.append({
                 "type": "time_stop",
                 "params": ParameterSpace.get_params("time_stop")
             })

        # Optional Logical Exit
        # exit_type = ParameterSpace.sample_exit_type()
        # ...

        # Filters
        filters = []
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
